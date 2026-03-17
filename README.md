# Automatic Pet Feeder Dashboard 🐾

An AI-integrated automatic pet feeder system built for **Raspberry Pi 3**. Features an interactive web dashboard, scheduled and manual feeding, real-time food level monitoring, AI-powered health suggestions, and pet status tracking.

---

## Features

| Feature | Description |
|---|---|
| **Interactive Dashboard** | Card-based UI showing pet profile, feeding times, food level, logs |
| **User Authentication** | Login & registration with password hashing |
| **Scheduled Feeding** | Set multiple daily feeding times; stepper motor auto-dispenses |
| **Manual Feeding** | One-click "Feed Now" button triggers the stepper motor |
| **Food Level Monitor** | HC-SR04 ultrasonic sensor measures remaining food in the container |
| **AI Suggestions** | Analyzes pet status + feeding history to recommend portion sizes, feeding times, and vet visits |
| **Pet Status Tracking** | Record conditions (sick, not eating, lethargic, etc.) with severity ratings |
| **Vet Recommendations** | AI urgency-based alerts when a vet visit is needed |

---

## Hardware Requirements

- Raspberry Pi 3 Model B
- Stepper Motor 28BYJ-48 with ULN2003 driver board (for dispensing food)
- HC-SR04 Ultrasonic Sensor (for measuring food level)
- I2C LCD display 16x2 (for status display)
- DS3231 RTC module (for accurate timekeeping)
- Jumper wires, breadboard
- 5V power supply
- Pet feeder enclosure / hopper

### Wiring Diagram

| Component | RPi GPIO Pin |
|---|---|
| Stepper IN1 (ULN2003) | GPIO 17 (Pin 11) |
| Stepper IN2 (ULN2003) | GPIO 18 (Pin 12) |
| Stepper IN3 (ULN2003) | GPIO 27 (Pin 13) |
| Stepper IN4 (ULN2003) | GPIO 22 (Pin 15) |
| HC-SR04 Trigger | GPIO 23 (Pin 16) |
| HC-SR04 Echo | GPIO 24 (Pin 18) |
| I2C LCD SDA | GPIO 2 (Pin 3) |
| I2C LCD SCL | GPIO 3 (Pin 5) |
| DS3231 RTC SDA | GPIO 2 (Pin 3) — shared I2C bus |
| DS3231 RTC SCL | GPIO 3 (Pin 5) — shared I2C bus |
| HC-SR04 VCC | 5V (Pin 2 or 4) |
| HC-SR04 GND | GND |
| Stepper / LCD / RTC VCC | 3.3V or 5V (Pin 1, 2, or 4) |
| Stepper / LCD / RTC GND | GND (Pin 6, 9, 14, etc.) |

> **Note:** Use a voltage divider on the HC-SR04 Echo pin (5V → 3.3V) to protect the Pi's GPIO.
> The LCD (0x27) and DS3231 RTC (0x68) share the same I2C bus — no conflicts.
> Enable I2C on the Raspberry Pi via `sudo raspi-config` → Interface Options → I2C.

---

## Software Setup

### 1. Clone / Copy to Raspberry Pi

```bash
# Copy the PetFeeder folder to your Pi
scp -r PetFeeder/ pi@<your-pi-ip>:~/
```

### 2. Install Dependencies

```bash
cd ~/PetFeeder
python3 -m venv venv
#(Windows)
venv/Scripts/Activate
#(MacOS/Linux)
source venv/bin/activate
pip install -r requirements.txt

# On Raspberry Pi, also install GPIO and enable I2C:
pip install RPi.GPIO
sudo raspi-config  # Enable I2C under Interface Options
sudo usermod -aG gpio pi
```

### 3. Run the Application

```bash
python app.py
```

The dashboard will be available at: **http://\<your-pi-ip\>:5000**

### 4. Auto-start on Boot (Optional)

Create a systemd service:

```bash
sudo nano /etc/systemd/system/petfeeder.service
```

```ini
[Unit]
Description=Pet Feeder Dashboard
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/PetFeeder
ExecStart=/home/pi/PetFeeder/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable petfeeder
sudo systemctl start petfeeder
```

---

## Project Structure

```
PetFeeder/
├── app.py                 # Flask application & routes
├── config.py              # Configuration (GPIO pins, DB path)
├── models.py              # SQLAlchemy database models
├── ai_engine.py           # AI suggestion engine
├── hardware.py            # Raspberry Pi GPIO controller
├── requirements.txt       # Python dependencies
├── petfeeder.db           # SQLite database (auto-created)
├── static/
│   ├── css/style.css      # Dashboard stylesheet
│   ├── js/dashboard.js    # Frontend JavaScript
│   └── images/            # Pet photos, etc.
└── templates/
    ├── base.html           # Base template
    ├── login.html          # Login page
    ├── register.html       # Registration page
    ├── add_pet.html        # Add pet form
    └── dashboard.html      # Main dashboard
```

---

## Usage

1. **Register** an account and **log in**
2. **Add your pet** (name, breed, age, weight)
3. **Set feeding schedules** — the stepper motor will auto-trigger at those times (timed via DS3231 RTC)
4. Use **Feed Now** for manual dispensing
5. **Track pet status** — click status buttons (Sick, Not Eating, etc.)
6. View **AI Suggestions** for portion advice and vet visit recommendations
7. Monitor **Food Level** — refill when it drops below 25%

---

## Configuration

Edit `config.py` to change GPIO pins, stepper settings, sensor settings, or LCD address:

```python
# Stepper Motor 28BYJ-48 pins (ULN2003 IN1–IN4)
STEPPER_IN1 = 17
STEPPER_IN2 = 18
STEPPER_IN3 = 27
STEPPER_IN4 = 22

# HC-SR04 Ultrasonic Sensor
SENSOR_TRIGGER_PIN = 23
SENSOR_ECHO_PIN = 24
FOOD_CONTAINER_HEIGHT_CM = 20  # Height of container in cm

# I2C LCD
LCD_I2C_ADDRESS = 0x27  # Use 0x3F if 0x27 doesn't work

# DS3231 RTC — address is fixed at 0x68 (no config needed)
# Shares I2C bus with LCD

# Feeder
STEPS_PER_PORTION = 512  # Steps per portion (quarter revolution)
```

---

## Simulation Mode

When not running on a Raspberry Pi (no `RPi.GPIO` available), the hardware module runs in **simulation mode** — all GPIO actions are logged but no actual hardware is triggered. This lets you develop and test the dashboard on any computer.
