# 🐾 Automatic Pet Feeder – Complete Codebase Analysis

**Project Type:** IoT Application (Flask + Raspberry Pi + AI)  
**Purpose:** Automated pet feeding system with AI-powered health monitoring  
**Target Device:** Raspberry Pi 3 Model B  
**Status:** Feature-complete, ready for deployment

---

## 📋 Project Overview

The **Automatic Pet Feeder** is a comprehensive IoT solution designed to automate pet feeding while providing intelligent health monitoring and veterinary recommendations. It combines hardware control (stepper motor, ultrasonic sensor, RTC) with a modern web dashboard and AI-powered suggestions.

### Key Innovation
- **AI-Powered Feeding Suggestions**: Adjusts feeding recommendations based on pet health status, species, weight, and feeding history
- **Multi-User System**: Each user can manage one pet with separate authentication
- **Real-time Monitoring**: Track food levels, feeding logs, and pet health status
- **Hardware Integration**: Seamless Raspberry Pi GPIO control with fallback simulation mode

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│         Web UI (Jinja2 Templates)              │
│  • Dashboard  • Login  • Pet Management        │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│       Flask Web Server (Python)                │
│  • REST API endpoints  • Database ORM          │
│  • Session management  • Authentication        │
└──────────────────┬──────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
   ┌────▼────┐ ┌──▼────┐ ┌─▼──────────┐
   │  Models │ │AI Eng │ │  Hardware  │
   │ (SQLAlchemy)│      │ (GPIO/I2C) │
   └────┬────┘ └──┬────┘ └─┬──────────┘
        │         │        │
        └─────────┼────────┘
                  │
        ┌─────────▼────────┐
        │  SQLite Database │
        │ (Persistent Data)│
        └──────────────────┘
```

---

## 📁 File Structure & Purpose

### **Backend Python Files**

#### `app.py` (Main Application - ~550 lines)
**Responsibility:** Flask application entry point and route handler

**Key Features:**
- **Authentication Routes** (`/login`, `/register`, `/logout`): User authentication with Flask-Login
- **Dashboard** (`/dashboard`): Main interface showing pet profile, feeding times, food level, AI suggestions
- **Pet Management** (`/add-pet`, `/edit-pet`): CRUD operations for pet profiles
- **Feeding Control**:
  - `/api/schedule`: Save feeding schedules (time + portion size)
  - `/api/feed-now`: Manual feeding trigger
  - `/api/feeding-logs`: Paginated feeding history
- **Pet Status Tracking** (`/api/pet-status`): Record health issues (sick, not eating, lethargic, etc.)
- **AI Integration** (`/api/ai-suggestions`): Fetch feeding recommendations
- **Background Scheduler**: APScheduler runs `check_and_feed()` every minute to automatically dispense food at scheduled times
- **Food Level Endpoint** (`/api/food-level`): Real-time ultrasonic sensor readings

**Technology Stack:**
- Flask 3.1.x
- Flask-SQLAlchemy for ORM
- Flask-Login for authentication
- APScheduler for background scheduling
- Werkzeug for password hashing

---

#### `models.py` (Database Schema - ~80 lines)
**Responsibility:** SQLAlchemy ORM models defining database structure

**Database Tables:**
1. **`User`**: Account credentials, relationships to pets
   - Fields: username, email, password_hash, created_at
   - Relationship: owns Pet records

2. **`Pet`**: Individual pet profiles
   - Fields: name, species, breed, age (in months), weight_kg, photo_url
   - Relationships: has many PetStatus, FeedingLog, FeedingSchedule

3. **`PetStatus`**: Health and behavior tracking
   - Fields: status_type (enum), description, severity (1-5), recorded_at, is_active
   - Types: sick, not_eating, timid, vomiting, lethargic, diarrhea, overweight, energetic, normal
   - One status type per pet at a time (others deactivated on new entry)

4. **`FeedingSchedule`**: Recurring feeding times
   - Fields: feed_time (HH:MM format), portion_size (multiplier), is_active
   - Multiple schedules per pet allowed

5. **`FeedingLog`**: Historical record of all feeding events
   - Fields: feed_type ("Scheduled" or "Manual"), portion_size, fed_at, notes

**Design Pattern:** Follows Flask-SQLAlchemy conventions with cascade delete relationships

---

#### `config.py` (Configuration - ~20 lines)
**Responsibility:** Centralized configuration for the application

**Configuration Parameters:**

| Category | Parameter | Value | Purpose |
|----------|-----------|-------|---------|
| **API** | OPENROUTER_API_KEY | (Secret) | AI chatbox integration |
| ** | SECRET_KEY | Random hexdigest | Flask session encryption |
| **Database** | SQLALCHEMY_DATABASE_URI | sqlite:///petfeeder.db | Local SQLite persistence |
| **Stepper Motor** | STEPPER_IN1–IN4 | GPIO 17,18,27,22 | ULN2003 driver pins |
| **Stepper Motor** | STEPPER_DELAY | 0.002s | Step timing (controls speed/torque) |
| **Ultrasonic Sensor** | SENSOR_TRIGGER_PIN | GPIO 23 | HC-SR04 trigger |
| **Ultrasonic Sensor** | SENSOR_ECHO_PIN | GPIO 24 | HC-SR04 echo |
| **Ultrasonic Sensor** | FOOD_CONTAINER_HEIGHT_CM | 20cm | Container height for level calculation |
| **LCD Display** | LCD_I2C_ADDRESS | 0x27 | I2C address (try 0x3F if not working) |
| **LCD Display** | LCD_COLS, LCD_ROWS | 16×2 | Display dimensions |
| **Feeder** | STEPS_PER_PORTION | 512 | Stepper steps per food portion |

**Design Pattern:** Class-based config can be overridden per environment

---

#### `hardware.py` (Hardware Abstraction - ~250 lines)
**Responsibility:** GPIO control and sensor interface with simulation fallback

**Class: `FeederHardware`**

**Motor Control:**
- `_step_motor(steps, direction)`: Half-step sequencing for 28BYJ-48 motor
- `dispense_food(portion_multiplier)`: Dispense food (1.0x = 512 steps)
- Uses HALF_STEP_SEQ for smooth motion and power efficiency
- All coils disabled after motion to prevent overheating

**Ultrasonic Sensor (Food Level):**
- `_measure_distance_cm()`: Sends 10µs pulse, measures echo time
- `get_food_level()`: Converts distance to percentage (0-100%)
- Formula: `Level% = (container_height - distance) / container_height × 100`
- `get_food_level_label()`: Returns human-friendly labels (Full, Half Full, Low, Very Low)

**Real-Time Clock (DS3231 RTC):**
- `get_rtc_time()`: Reads accurate time from DS3231 module
- `set_rtc_time(dt)`: Syncs RTC to system clock or manual datetime
- `get_current_time_str()`: Returns HH:MM format for scheduler

**LCD Display (16×2 I2C):**
- `lcd_show_message(line1, line2)`: Display two-line text
- `lcd_show_status(food_level, next_feed)`: Show food & next feeding time

**Simulation Mode:**
- Activates when RPi.GPIO unavailable (Windows/Mac development)
- Simulates food level decline on dispense
- Gracefully logs all actions

**Hardware Fallback Strategy:**
```
If RPi available:
  ✓ Use real GPIO
  ✓ Control stepper motor
  ✓ Read sensors
Else:
  ✓ Log operations
  ✓ Simulate food level
  ✓ Continue without hardware
```

---

#### `ai_engine.py` (AI Suggestions - ~200 lines)
**Responsibility:** Intelligent feeding recommendations and health analysis

**Core Algorithm: `get_feeding_suggestion(pet, active_statuses, feeding_logs, schedules)`**

**1. Status-Based Adjustments:**
```python
STATUS_FEEDING_ADJUSTMENTS = {
  "sick": portion_modifier=0.7, vet_urgency=3
  "not_eating": portion_modifier=0.5, vet_urgency=4 ← URGENT
  "vomiting": portion_modifier=0.5, vet_urgency=4 ← URGENT
  "diarrhea": portion_modifier=0.6, vet_urgency=3
  "lethargic": portion_modifier=0.8, vet_urgency=3
  "overweight": portion_modifier=0.8, vet_urgency=2
  "timid": portion_modifier=0.9, vet_urgency=1
  "energetic": portion_modifier=1.1, vet_urgency=0
  "normal": portion_modifier=1.0, vet_urgency=0
}
```
Combined modifier = minimum of all active conditions

**2. Species & Weight Guidelines:**
```python
SPECIES_GUIDELINES = {
  "Dog": [(0-5kg, 0.5-1.0 cups), (5-10kg, 1.0-1.5), ...],
  "Cat": [(0-3kg, 0.25-0.5 cups), ...]
}
```
Baseline is multiplied by combined status modifier

**3. Feeding Time Suggestions:**
- If schedules exist: Use existing times
- If Cat: Suggest 3x daily (morning, noon, evening)
- If young pet (<1 month): Suggest 4x daily
- Otherwise: Default 2x daily (morning, evening)

**4. Analysis Output:**
```python
{
  "suggested_times": ["08:00", "18:00"],
  "portion_advice": "Recommended daily intake: 1.2–1.5 cups/day",
  "warnings": ["Feed smaller portions when sick"],
  "overall_status": "good|caution|warning|critical",
  "vet_recommendation": "Suggested action based on urgency"
}
```

**5. Vet Urgency Tiers:**
- **Urgency 0-1**: No immediate action. Annual check-up recommended.
- **Urgency 2**: Routine check-up recommended.
- **Urgency 3**: Visit within few days - `overall_status: "warning"`
- **Urgency 4-5**: URGENT vet visit - `overall_status: "critical"`

**Helper Functions:**
- `get_next_feeding_time(schedules)`: Returns upcoming feed time (or first tomorrow)
- `format_time_12h(time_24h)`: Converts "14:00" → "2:00 PM"

---

### **Frontend Files**

#### `templates/base.html` (Layout Template - ~30 lines)
**Responsibility:** Jinja2 base template that all pages extend

**Features:**
- Meta tags for responsiveness
- Font import (Nunito from Google Fonts)
- Stylesheet link
- Block placeholders: `title`, `body_class`, `content`, `scripts`
- Clean separation of concerns

---

#### `templates/login.html` (Authentication - ~40 lines)
**Features:**
- Username and password fields
- Form validation on POST
- Flash messages for errors
- Link to registration
- Redirects to dashboard on success
- Card-based responsive design

**User Flow:**
1. User enters credentials
2. Form POSTs to `/login`
3. Backend validates with `user.check_password()`
4. Sets Flask-Login session
5. Redirects to `/dashboard`

---

#### `templates/add_pet.html` (Pet Profile Registration - ~60 lines)
**Form Fields:**
- Pet name (required)
- Species dropdown (Dog, Cat, Other)
- Custom species input (if "Other" selected)
- Breed
- Age (separate year/month inputs)
- Weight (kg)
- Photo URL (optional)

**Validation:**
- Name required
- Backend converts years/months to total months
- Placeholder values for easier input

---

#### `templates/dashboard.html` (Main Interface - ~200 lines, truncated)
**Dashboard Grid Layout (3-column):**

1. **Welcome Card**
   - Pet avatar (photo or placeholder emoji)
   - Pet name, breed, age, weight
   - Edit Pet button (opens modal)

2. **Next Feeding Time Card**
   - Clock icon
   - Large display of next scheduled feed time
   - Scheduled label

3. **Food Level Card**
   - Visual feeder container
   - Percentage bar
   - Food level label (Full/Half Full/Low/Very Low)
   - Refreshes every 30 seconds

4. **Feeding Schedules Card** (Additional)
   - List of all scheduled times
   - Remove buttons for each schedule
   - Add new schedule form with time picker

5. **Manual Feed Card**
   - "Feed Now" button
   - Triggers immediate dispensing

6. **Pet Status Card**
   - Status buttons: Sick, Not Eating, Timid, Vomiting, Lethargic, Diarrhea, Overweight, Energetic, Normal
   - Active statuses list with severity dots
   - Detail form (on button click)

7. **AI Suggestions Card**
   - Overall status badge (good/caution/warning/critical)
   - Portion advice with daily intake recommendation
   - Vet recommendation with urgency-based messaging
   - Warning list
   - Refresh button

8. **Recent Feeding Logs Card**
   - List of last 10 feedings
   - Type (Scheduled/Manual), time, portion

9. **AI Chatbox Widget** (Fixed bottom-right)
   - OpenRouter AI integration
   - Chat history maintained
   - Can ask questions about pet feeding, health, etc.

**Key Interactions:**
- Time pickers for schedules (12-hour AM/PM converted to 24-hour)
- Modal overlay for pet editing
- Toast notifications on success/error
- Real-time clock updates (every second)
- Food level polling (every 30 seconds)

---

#### `static/js/dashboard.js` (Frontend Logic - ~250 lines)
**Core Functionality:**

**1. Authentication & Session**
- Checks for login requirement
- User loader decorator

**2. UI Helpers**
- `toast(msg, type)`: Show temporary notification
- `api(url, options)`: Fetch wrapper with error handling

**3. Live Clock**
- Updates every 1 second
- Converts to 12-hour format
- Shows in top bar

**4. Schedule Management**
- Save schedule: Convert 12h time to 24h, POST to `/api/schedule`
- Delete schedule: DELETE request to `/api/schedule/{id}`
- Add newly created schedule to DOM
- Remove deleted schedule from DOM

**5. Manual Feeding**
- "Feed Now" button disabled during dispensing
- Shows "Dispensing..." state
- Updates food level after completion
- Adds new entry to logs
- Shows completion toast

**6. Pet Status Tracking**
- Status buttons trigger detail form modal
- Severity slider (1-5) with label display
- Optional description textarea
- Submit updates AI suggestions
- Display active statuses with dots (●○○○○ = severity 1)
- Resolve button to deactivate status

**7. AI Suggestions**
- Updates on status change
- Refresh button for manual update
- Displays badge, portion advice, vet recommendation, warnings

**8. Periodic Updates**
- Food level every 30 seconds
- Updates label and percentage

**9. AI Chatbox**
- Sends message to `/api/chat`
- Maintains chat history
- Shows OpenRouter API model responses
- Close button hides widget

**10. Pet Editing**
- Modal dialog with confirmation
- Pre-fills current pet details
- POST to `/edit-pet`

---

#### `static/css/style.css` (Styling - ~200 lines)
**Design System:**

**Color Palette:**
- Primary teal: `#1a8a6e` (nav, buttons)
- Primary light: `#23a882` (hover states)
- Primary dark: `#14705a`
- Nav background: `#1b3a4b`
- Accent green: `#4caf50` (primary buttons)
- Background gradient: Soft greens (#c8e6c9 → #80cbc4)

**Component Styles:**

| Component | Styling | Purpose |
|-----------|---------|---------|
| Body | Gradient background fixed attachment | Consistent throughout scrolling |
| Cards | 16px radius, white background, shadow | Clean separated sections |
| Buttons | Rounded, font-weight 700, transitions | Clear call-to-actions |
| Inputs | 8px radius, light border, focus shadow | Consistent form elements |
| Auth pages | Centered flex layout, 420px max-width | Mobile-friendly login/register |
| Top bar | Sticky positioning, dark background | Always visible navigation |

**Typography:**
- Font: Nunito from Google Fonts (fallback: system fonts)
- Base size: 15px (html)
- Font weights: 400 (regular), 600 (semibold), 700 (bold), 800 (extra bold)

**Responsive Design:**
- Dashboard grid: 3 columns (likely has media queries for smaller screens - truncated in read)
- Form rows: Flex with gap spacing
- Mobile-first with flexbox/grid

---

## 🔄 Data Flow Examples

### Scenario 1: Scheduled Feeding
```
1. User sets feeding schedule (08:00 AM, 1.0 portion) via dashboard
   → POST /api/schedule {feed_time: "08:00", portion_size: 1.0}
   
2. Schedule saved to database
   → FeedingSchedule(pet_id=1, feed_time="08:00", is_active=True)
   
3. Background scheduler (APScheduler) checks every minute
   → check_and_feed() filters schedules with current_minutes ±1
   
4. At 08:00 (within ±1 min window):
   → feeder.dispense_food(1.0) triggers stepper motor (512 steps)
   → FeedingLog created: {pet_id=1, feed_type="Scheduled", portion_size=1.0, fed_at=now}
   
5. Frontend polls /api/food-level every 30 seconds
   → Shows updated food level after dispensing
```

### Scenario 2: Pet Health Status Alert
```
1. User records pet is "sick" with severity 3 via status buttons
   → POST /api/pet-status {status_type: "sick", severity: 3, description: "..."}
   
2. Backend saves PetStatus(pet_id=1, status_type="sick", is_active=True)
   
3. Existing "normal" status deactivated (only one active per type)
   
4. AI engine recalculates suggestions:
   → STATUS_FEEDING_ADJUSTMENTS["sick"].portion_modifier = 0.7
   → portion_advice: "0.35–0.7 cups/day (adjusted for current status)"
   → vet_urgency: 3 → overall_status: "warning"
   → vet_recommendation: "We recommend scheduling a veterinary visit..."
   
5. Frontend updates AI card with badge + recommendations
   → Displays warning list
```

### Scenario 3: AI Chatbox Interaction
```
1. User types in chatbox: "Should I increase my dog's portions?"
   → POST /api/chat {message: "...", history: [...]}
   
2. Backend calls openrouter_chat(message, history)
   → Builds messages array with conversation history
   → Sends to OpenRouter API (openchat/openchat-3.5-0106 model)
   
3. AI response received and displayed in chatbox
   → Appended to DOM with bot styling
   
4. History maintained for context in next message
```

---

## 🐛 Current Issues & Observations

### Security Concerns
1. **API Key Exposed**: `config.py` has OpenRouter API key hardcoded (should be env variable only)
   ```python
   # VULNERABLE:
   OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") or "sk-or-v1-..."
   ```
   **Fix:** Remove the hardcoded fallback, require environment variable

2. **Password Security**: Uses Werkzeug's `generate_password_hash` (PBKDF2 with sha256) ✅ Secure
3. **CSRF Protection**: No explicit CSRF tokens on forms (vulnerable if no CSRF middleware configured)

### Backend Logic Issues
1. **Time Window Bug**: `check_and_feed()` creates window list as strings but compares with query
   ```python
   window = [f"{((current_minutes + offset) // 60) % 24:02d}:..." for offset in (-1, 0, 1)]
   # Compares with FeedingSchedule.feed_time (stored as strings) ✅ Correct approach
   ```

2. **Floating Point Risk**: Portion sizes stored as floats, no validation on extreme values
   ```python
   portion = float(data.get("portion_size", 1.0))  # No bounds checking
   ```

3. **Missing Transaction Management**: No rollback on errors in scheduled feeding

### Frontend Issues
1. **No Loading States**: Feed button shows state, but schedule operations don't
2. **Chat History Memory Leak**: `chatHistory` array grows without limit
3. **Time Conversion**: 12h to 24h conversion has edge case:
   ```javascript
   if (ampm === "PM" && hour !== 12) hour += 12;  // 12 PM stays 12 (correct)
   if (ampm === "AM" && hour === 12) hour = 0;    // 12 AM becomes 0 (correct)
   ```
   ✅ Logic is correct

### Database Design
1. **Single Pet Limitation**: One user → one pet (by design). Consider multi-pet support future.
2. **No Audit Trail**: FeedingLog is immutable, but PetStatus soft-deletes only. Consider hard delete timestamps.
3. **No Backup Strategy**: SQLite database not cloud-backed

### Hardware Integration
1. **GPIO Cleanup**: Properly registered with `atexit` ✅ Good
2. **Sensor Timeout**: 40ms timeout might be too generous for HC-SR04
3. **RTC Battery**: DS3231 has backup battery, but no initial sync on boot

---

## 📊 Statistics

| Metric | Value |
|--------|-------|
| Total Python Lines | ~1100 |
| Total JavaScript Lines | ~250 |
| Total CSS Lines | ~200+ (truncated) |
| Database Tables | 5 |
| API Endpoints | 15+ |
| UI Components | 9 major cards |
| Status Types | 9 |
| Hardware Interfaces | 4 (motor, sensor, LCD, RTC) |

---

## 🚀 Deployment Checklist

### Pre-deployment
- [ ] Set `OPENROUTER_API_KEY` environment variable (remove hardcoded key)
- [ ] Set `SECRET_KEY` environment variable (or keep random per session)
- [ ] Enable I2C on Raspberry Pi: `sudo raspi-config` → Interface Options
- [ ] Test GPIO pins in simulation mode first
- [ ] Calibrate ultrasonic sensor with known food levels

### Hardware Setup
- [ ] Wire stepper motor to GPIO 17,18,27,22
- [ ] Wire HC-SR04 trigger to GPIO 23, echo to GPIO 24 (with voltage divider!)
- [ ] Connect I2C LCD (0x27) and RTC (0x68) on I2C bus
- [ ] Test motor rotation and sensor readings
- [ ] Verify DS3231 RTC time accuracy

### Runtime
- [ ] Run with `python app.py` or systemd service
- [ ] Monitor scheduler logs for feeding events
- [ ] Set up log rotation for production use
- [ ] Implement database backups

---

## 🎯 Recommendations for Enhancement

1. **Multi-Pet Support**: Extend to support multiple pets per user
2. **CSRF Protection**: Add Flask-WTF for form token validation
3. **Rate Limiting**: Add Flask-Limiter to prevent API abuse
4. **Monitoring**: Add health check endpoint and alerting
5. **Data Export**: Allow CSV/JSON export of feeding logs
6. **Mobile App**: React Native companion app
7. **Cloud Sync**: Optional Firebase sync for remote access
8. **Camera Integration**: Add PiCamera for pet monitoring
9. **Humidity/Temperature**: Extend sensor suite for environmental data
10. **Predictive Feeding**: Use ML to optimize feeding times based on pet behavior

---

## 📝 Summary

This is a **well-architected IoT application** with clear separation of concerns:
- **Backend**: Robust Flask API with APScheduler for automation
- **Database**: Normalized SQLAlchemy models with proper relationships
- **Hardware**: Abstraction layer with graceful fallback for simulation
- **Frontend**: Responsive dashboard with real-time updates
- **AI**: Rule-based suggestion engine (upgradeable to ML/LLM)

**Strengths:**
✅ Clean code organization  
✅ Hardware abstraction layer  
✅ AI-powered recommendations  
✅ Real-time sensor integration  
✅ Responsive UI  
✅ Background task scheduling  

**Areas for Improvement:**
⚠️ Security hardening (remove API key)  
⚠️ Input validation on portion sizes  
⚠️ CSRF protection  
⚠️ Multi-pet architecture  
⚠️ Error recovery in scheduler  

**Production Readiness:** 7/10 (needs security hardening and testing)
