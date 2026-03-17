import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # OpenRouter API Key — hardcoded (set your own key here)
    # Get your key at: https://openrouter.ai/
    OPENROUTER_API_KEY = "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"
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "petfeeder.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Stepper Motor 28BYJ-48 via ULN2003 driver
    STEPPER_IN1 = 17
    STEPPER_IN2 = 18
    STEPPER_IN3 = 27
    STEPPER_IN4 = 22
    STEPPER_DELAY = 0.002  # Increased delay for more torque (power)

    # HC-SR04 Ultrasonic Sensor (food level)
    SENSOR_TRIGGER_PIN = 23  # Trigger pin
    SENSOR_ECHO_PIN = 24     # Echo pin
    FOOD_CONTAINER_HEIGHT_CM = 20  # Height of food container in cm

    # DS3231 RTC (I2C address 0x68 — fixed, no config needed)
    # Shares the I2C bus (SDA/SCL) with the LCD

    # I2C LCD (16x2)
    LCD_I2C_ADDRESS = 0x27  # Common address; use 0x3F if 0x27 doesn't work
    LCD_COLS = 16
    LCD_ROWS = 2

    # Feeder settings
    STEPS_PER_PORTION = 512  # Stepper steps per portion (quarter revolution)
