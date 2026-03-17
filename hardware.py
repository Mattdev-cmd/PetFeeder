"""
Hardware abstraction layer for Raspberry Pi GPIO.
Controls the stepper motor 28BYJ-48 (feeder), HC-SR04 ultrasonic sensor
(food level), I2C LCD display, and DS3231 RTC for accurate timekeeping.
Falls back to simulation mode when not running on a Raspberry Pi.
"""

import time
import logging

logger = logging.getLogger(__name__)

# ── Hardware library imports ─────────────────────────────────────────────────

RPI_AVAILABLE = False
LCD_AVAILABLE = False
RTC_AVAILABLE = False

try:
    import RPi.GPIO as GPIO
    RPI_AVAILABLE = True
except ImportError:
    logger.info("RPi.GPIO not available — running in simulation mode.")

try:
    from RPLCD.i2c import CharLCD
    LCD_AVAILABLE = True
except ImportError:
    logger.info("RPLCD library not available — LCD will be simulated.")

try:
    import adafruit_ds3231
    import board
    import busio
    RTC_AVAILABLE = True
except ImportError:
    logger.info("DS3231 library not available — using system clock.")


# Half-step sequence for 28BYJ-48 via ULN2003 driver
HALF_STEP_SEQ = [
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1],
]


class FeederHardware:
    """Controls the physical pet feeder hardware."""

    def __init__(
        self,
        stepper_pins=(17, 18, 27, 22),
        trigger_pin=23,
        echo_pin=24,
        container_height_cm=20,
        steps_per_portion=512,
        step_delay=None,
        lcd_address=0x27,
        lcd_cols=16,
        lcd_rows=2,
    ):
        self.stepper_pins = stepper_pins
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.container_height_cm = container_height_cm
        self.steps_per_portion = steps_per_portion
        # Use config value if not provided
        from config import Config
        self.step_delay = step_delay if step_delay is not None else Config.STEPPER_DELAY
        self.lcd_address = lcd_address
        self.lcd_cols = lcd_cols
        self.lcd_rows = lcd_rows

        self._lcd = None
        self._rtc = None
        self._simulated_food_level = 50  # percentage for simulation mode

        if RPI_AVAILABLE:
            self._setup_gpio()
        if LCD_AVAILABLE and RPI_AVAILABLE:
            self._setup_lcd()
        if RTC_AVAILABLE and RPI_AVAILABLE:
            self._setup_rtc()

    # ── Setup ────────────────────────────────────────────────────────────

    def _setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Stepper motor pins (ULN2003 IN1–IN4)
        for pin in self.stepper_pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, 0)

        # Ultrasonic sensor HC-SR04
        GPIO.setup(self.trigger_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        GPIO.output(self.trigger_pin, False)

    def _setup_lcd(self):
        try:
            self._lcd = CharLCD(
                i2c_expander="PCF8574",
                address=self.lcd_address,
                port=1,
                cols=self.lcd_cols,
                rows=self.lcd_rows,
                dotsize=8,
            )
            self._lcd.clear()
            self._lcd.write_string("Pet Feeder\r\nReady!")
            logger.info("I2C LCD initialized.")
        except Exception as e:
            logger.error(f"Error initializing I2C LCD: {e}")
            self._lcd = None

    def _setup_rtc(self):
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self._rtc = adafruit_ds3231.DS3231(i2c)
            logger.info("DS3231 RTC initialized.")
        except Exception as e:
            logger.error(f"Error initializing DS3231 RTC: {e}")
            self._rtc = None

    # ── Stepper motor control ────────────────────────────────────────────

    def _step_motor(self, steps, direction=1):
        """
        Rotate the 28BYJ-48 stepper motor a given number of half-steps.
        direction: 1 = forward (dispense), -1 = reverse
        """
        seq = HALF_STEP_SEQ if direction == 1 else HALF_STEP_SEQ[::-1]
        for i in range(steps):
            for pin_index, pin in enumerate(self.stepper_pins):
                GPIO.output(pin, seq[i % len(seq)][pin_index])
            time.sleep(self.step_delay)

        # Turn off all coils to save power and prevent overheating
        for pin in self.stepper_pins:
            GPIO.output(pin, 0)

    def dispense_food(self, portion_multiplier=1.0):
        """Activate stepper motor to dispense food."""
        steps = int(self.steps_per_portion * portion_multiplier)

        if RPI_AVAILABLE:
            try:
                self._step_motor(steps, direction=1)
                logger.info(f"Food dispensed ({steps} steps, portion x{portion_multiplier})")
                self.lcd_show_message("Dispensing...", "Done!")
                return True
            except Exception as e:
                logger.error(f"Error dispensing food: {e}")
                return False
        else:
            # Simulation mode
            self._simulated_food_level = max(0, self._simulated_food_level - 5)
            logger.info(
                f"[SIM] Food dispensed ({steps} steps). "
                f"Level now {self._simulated_food_level}%"
            )
            return True

    # ── Ultrasonic sensor (food level) ────────────────────────────────────

    def _measure_distance_cm(self):
        """
        Send an ultrasonic pulse and measure the echo return time.
        Returns distance in centimetres.
        """
        GPIO.output(self.trigger_pin, True)
        time.sleep(0.00001)
        GPIO.output(self.trigger_pin, False)

        start_time = time.time()
        stop_time = time.time()
        timeout = start_time + 0.04  # 40 ms timeout

        while GPIO.input(self.echo_pin) == 0:
            start_time = time.time()
            if start_time > timeout:
                break

        timeout = start_time + 0.04
        while GPIO.input(self.echo_pin) == 1:
            stop_time = time.time()
            if stop_time > timeout:
                break

        elapsed = stop_time - start_time
        distance_cm = (elapsed * 34300) / 2  # speed of sound
        return distance_cm

    def get_food_level(self):
        """
        Read the HC-SR04 ultrasonic sensor to estimate food level.
        Measures distance from sensor (mounted at top of container) to
        food surface. Less distance = more food.
        Returns percentage 0–100.
        """
        if RPI_AVAILABLE:
            try:
                distance = self._measure_distance_cm()
                level = (self.container_height_cm - distance) / self.container_height_cm * 100
                level = max(0, min(100, level))
                return round(level)
            except Exception as e:
                logger.error(f"Error reading ultrasonic sensor: {e}")
                return -1
        else:
            return self._simulated_food_level

    def get_food_level_label(self, percentage):
        """Return a human-friendly label for food level."""
        if percentage >= 80:
            return "Full"
        elif percentage >= 50:
            return "Half Full"
        elif percentage >= 25:
            return "Low"
        else:
            return "Very Low"

    # ── DS3231 RTC ───────────────────────────────────────────────────────

    def get_rtc_time(self):
        """Read current time from the DS3231 RTC. Returns a datetime object."""
        if self._rtc:
            try:
                t = self._rtc.datetime
                from datetime import datetime
                return datetime(t.tm_year, t.tm_mon, t.tm_mday,
                                t.tm_hour, t.tm_min, t.tm_sec)
            except Exception as e:
                logger.error(f"Error reading RTC: {e}")
        from datetime import datetime
        return datetime.now()

    def set_rtc_time(self, dt=None):
        """
        Set the DS3231 RTC time. If dt is None, syncs from system clock.
        dt should be a datetime object.
        """
        if self._rtc:
            try:
                import time as _time
                if dt is None:
                    from datetime import datetime
                    dt = datetime.now()
                self._rtc.datetime = _time.struct_time(
                    (dt.year, dt.month, dt.day,
                     dt.hour, dt.minute, dt.second,
                     dt.weekday(), -1, -1)
                )
                logger.info(f"RTC time set to {dt}")
                return True
            except Exception as e:
                logger.error(f"Error setting RTC: {e}")
        return False

    def get_current_time_str(self):
        """Return current HH:MM string from RTC (or system clock as fallback)."""
        now = self.get_rtc_time()
        return f"{now.hour:02d}:{now.minute:02d}"

    # ── I2C LCD display ──────────────────────────────────────────────────

    def lcd_show_message(self, line1, line2=""):
        """Display a two-line message on the I2C LCD."""
        if self._lcd:
            try:
                self._lcd.clear()
                self._lcd.write_string(line1[:self.lcd_cols])
                if line2:
                    self._lcd.crlf()
                    self._lcd.write_string(line2[:self.lcd_cols])
            except Exception as e:
                logger.error(f"Error writing to LCD: {e}")
        else:
            logger.info(f"[SIM LCD] {line1} | {line2}")

    def lcd_show_status(self, food_level, next_feed="--:--"):
        """Show food level and next feeding time on the LCD."""
        self.lcd_show_message(
            f"Food: {food_level}%",
            f"Next: {next_feed}",
        )

    # ── Cleanup ──────────────────────────────────────────────────────────

    def cleanup(self):
        """Clean up GPIO and hardware resources."""
        if RPI_AVAILABLE:
            # Turn off stepper coils
            for pin in self.stepper_pins:
                try:
                    GPIO.output(pin, 0)
                except Exception:
                    pass
            GPIO.cleanup()
            logger.info("GPIO cleaned up")
        if self._lcd:
            try:
                self._lcd.clear()
            except Exception:
                pass


# Singleton instance
feeder = FeederHardware()
