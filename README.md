# Auto Game Bot

An AI bot that watches your game screen, decides what to do, and presses keys or clicks the mouse for you. It uses a vision AI model (your choice of provider) to read the screen every frame and pick the best action.

No coding knowledge is required to run this. Just follow the steps below.

---

## Credits

This project uses the Interception kernel driver by Francisco Lopes (oblitum) to send keyboard and mouse input at the kernel level, making it undetectable to most game input filters.

Project page: https://github.com/oblitum/Interception

Thank you to Francisco and all contributors to that project.

---

## What you need

- A Windows 10 or Windows 11 PC
- Python 3.10 or newer (3.12 recommended)
- An account with at least one of these AI providers:
  - Azure OpenAI (recommended, this is what the bot was built and tested with)
  - OpenAI
  - Google Gemini
  - Anthropic Claude
- A game running in windowed or full-screen mode on your primary monitor

---

## Step 1 — Prepare your BIOS (one time only)

The Interception driver is a test-signed kernel driver. Windows requires two things before it will load it.

**Disable Secure Boot**

1. Restart your PC.
2. Enter your BIOS/UEFI setup. The key varies by motherboard — common ones are F2, Delete, F10, or F12. Check your PC or motherboard manual.
3. Find the Secure Boot option. It is usually under the Boot or Security tab.
4. Set it to Disabled.
5. Save and exit.

Your PC will restart normally. The Secure Boot off setting stays until you change it back.

---

## Step 2 — Install the Interception driver (one time only)

1. Open the Start menu, search for PowerShell, right-click it and choose Run as administrator.
2. Navigate to the repository folder:
   ```
   cd "C:\path\to\Auto-Game-Bot"
   ```
3. Run the installer:
   ```
   .\Interception\Install-Win11.ps1
   ```
   The installer will:
   - Create a self-signed test certificate and trust it on your machine.
   - Re-sign the driver files with SHA-256 so Windows 11 accepts them.
   - Enable Test Signing mode in your boot settings (you will see a small watermark in the corner of your desktop after reboot — this is normal and expected).
   - Register the keyboard and mouse services in Windows.
4. Restart your PC when the installer finishes.

To uninstall the driver at any time, run:

```
.\Interception\Uninstall-Win11.ps1
```

Note: if the driver is not installed, the bot will still run but will use a basic Windows input method (SendInput) that some games may block.

---

## Step 3 — Set up Python

If you use conda (Anaconda or Miniconda):

```
conda create -n gamebotenv python=3.12
conda activate gamebotenv
pip install -r requirements.txt
```

If you use plain Python:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## Step 4 — Choose your AI provider and get credentials

You only need one. Pick the provider you have access to.

**Option A — Azure OpenAI (recommended)**

1. Go to https://portal.azure.com and open your Azure OpenAI resource.
2. Copy your Endpoint URL and one of the API Keys.
3. Note the name of your deployed model (e.g. gpt-4o or gpt-5-nano).

**Option B — OpenAI**

1. Go to https://platform.openai.com/api-keys and create a key.

**Option C — Google Gemini**

1. Go to https://aistudio.google.com/app/apikey and create a key.

**Option D — Anthropic Claude**

1. Go to https://console.anthropic.com/settings/keys and create a key.

---

## Step 5 — Configure the bot

1. Copy the example config file:
   ```
   copy .env.example .env
   ```
2. Open `.env` in any text editor (Notepad is fine).
3. Fill in only the section for your chosen provider. Leave the others commented out (lines starting with `#`).

Example for Azure OpenAI:

```
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_DEPLOYMENT_NAME=gpt-5-nano
```

Example for OpenAI:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

Example for Gemini:

```
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.0-flash
```

Example for Anthropic:

```
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

The bot automatically detects which provider has credentials set. If you have credentials for more than one provider and want to force a specific one, add this line:

```
LLM_PROVIDER=azure
```

Replace `azure` with `openai`, `gemini`, or `anthropic` as needed.

**Screen capture settings** — also in `.env`:

```
CAPTURE_X=0
CAPTURE_Y=0
CAPTURE_W=1280
CAPTURE_H=720
```

Set these to match your game window position and size on your screen. If your screen is 1920x1080, set `CAPTURE_W=1920` and `CAPTURE_H=1080`.

---

## Step 6 — Run the bot

Make sure your game is open and on screen, then run:

```
python main.py
```

The bot will show a menu asking which game you are playing. Type the number next to your game and press Enter.

```
============================================================
  Select a game config
============================================================
  [1] Metal Gear Solid V: The Phantom Pain
  [0] Use default key map (no game selected)
============================================================
  Enter number:
```

Press Ctrl+C at any time to stop the bot cleanly.

---

## Adding a game config

Game configs live in the `games_config/` folder. Each game gets its own subfolder with a `config.json` that maps action names to keys. See `games_config/README.md` for instructions on adding a new game.

---

## Troubleshooting

**"No LLM credentials found" error**
Your `.env` file is missing or the keys are not filled in. Re-read Step 5.

**Bot presses wrong keys**
The key bindings in the game config may not match your in-game settings. Open `games_config/<game>/config.json` and update the keys to match your layout.

**Driver not working, input goes through SendInput instead**

- Check that Secure Boot is disabled in your BIOS.
- Make sure you ran the installer as Administrator and rebooted.
- Run `sc query keyboard` in a command prompt. It should say `STATE: 4 RUNNING`.

**Screen capture is black or wrong area**
Check `CAPTURE_W` and `CAPTURE_H` in your `.env`. They must match your actual screen or game window size.

---

## Contributing

Contributions are very welcome. Whether it is a new game config, a bug fix, or a new feature — feel free to open a pull request or an issue.

For a full technical explanation of how the code works and the project structure, see [developers.md](developers.md).
