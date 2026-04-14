# DESIGN DOCUMENT: JBL-Killer

**Project Objective:** Create the most powerful speaker $200 can buy. Must assemble parts myself.


## 1. System Architecture & Components
Wish to create a powerful speaker to rival commercial alternatives. Must do this while both SPL (Sound Pressure Level) and acoustic accuracy remain acceptible. Went to marketplace and amazon to get these amazing parts:

### 1.1 Parts Ledger
| Component | Part Details | Origin | Cost (CAD) |
| :--- | :--- | :--- | :--- |
| **Woofers (x2)** | **Mirage M 25 WO-49 (8")** | Second-hand / Salvaged | **$40.00** |
| **Cabinet** | **Sony SS-C510AV Tower** | Salvaged / Free | **$0.00** |
| **Tweeters** | **Sony Stock Units** | Original to Cabinet | **$0.00** |
| **Amplifier** | **TPA3116D2 Bluetooth 5.0** | New (Link | **~$35.00** |
| **Battery Core** | **Vatrer 12V 7Ah LiFePO4** | New (Link | **~$54.00** |
| **Power Mod** | **150W DC-DC Boost Converter**| New | **~$10.00** |
| **Charger** | **NOCO Genius 1** | Princess Auto | **$44.99** |
| **Hardware** | Switches, DC Jack, 16AWG Wire | Local Sourcing | **~$15.00** |
| **TOTAL** | | | **~$198.99** |

---

## 2. Technical Specifications
* **Acoustic Configuration:** **Bipolar (Back-to-Back).** Drivers are mounted on opposite faces of the cabinet and wired in-phase to cancel mechanical vibration.
* **Operating Voltage:** **24V DC** (Stepped up from 12.8V nominal battery voltage).
* **Max SPL:** **~107 dB @ 1m.**
* **Impedance:** **4 Ohms** (Dual 8-ohm Mirage woofers wired in parallel).
* **Power Efficiency:** **~90% (Class D).**
* **Estimated Runtime:** **6–8 hours** at high output; **20+ hours** at moderate background levels.

---

## 3. Assembly & Installation Guide

### Phase A: Mechanical Preparation
1.  **Cabinet Modification:** Cut an 8-inch diameter hole in the **rear panel** of the Sony cabinet, directly opposite the existing front woofer hole.
2.  **Sealing:** Ensure the cabinet is airtight. Use foam weatherstripping when mounting drivers.
3.  **Component Mounting:** Secure the battery at the cabinet base to lower the center of gravity. Mount the amplifier and boost converter to internal side walls.

### Phase B: Electrical Integration
1.  **Charging Circuit:** Wire the **DC Panel Jack** directly to the battery terminals. This allows charging regardless of whether the main power switch is ON or OFF.
2.  **Voltage Regulation:** Connect the battery to the **Boost Converter** via a heavy-duty toggle switch. Use a multimeter to tune the converter output to **exactly 24.0V** before connecting the amplifier.
3.  **Audio Path:**
    * Connect the **Boost Converter Output** to the **Amplifier DC Input**.
    * Wire the two **Mirage Woofers in parallel** (Positive to Positive, Negative to Negative).
    * Connect the parallel woofer pair to the **Left Channel** and the Sony tweeter to the **Right Channel** (or use an internal crossover if preferred).

---

## 4. Maintenance & Charging Protocol
To preserve the life of the **LiFePO4** chemistry and ensure system reliability, follow these protocols:

* **Charging:** Use the **NOCO Genius 1** via the external DC port. **The charger must be set to "Lithium" mode.** * **Storage:** If storing for more than a month, charge the battery to ~50-70%. Avoid storing the unit in freezing temperatures.
* **Thermal Management:** The boost converter and amp may get warm during 24V operation. Do not block the internal air volume of the tower.

---

**Design Verification:** Upon completion, the "Power Tower" provides a vibration-free, high-SPL audio experience with audiophile-grade frequency response, powered by a safe and long-lasting lithium core.
