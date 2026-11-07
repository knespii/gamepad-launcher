# Gamepad Launcher

Zmáčkni tlačítko **Home** na ovladači a vyber si, co chceš spustit: **Steam** v režimu Big Picture, **Heroic Games Launcher** v console módu na celou obrazovku, nebo **vypni PC**. Celé to ovládáš jen ovladačem, bez myši a klávesnice.

*English: Press the Home/Guide button on your gamepad to get a fullscreen menu: Steam Big Picture, Heroic (console mode, fullscreen) or power off. Linux, no root, no extra Python packages.*

## Jak to funguje

- Malý program na pozadí čte ovladač přímo z `/dev/input`.
- Po stisku **Home** ukáže menu přes celou obrazovku.
- Když už Steam běží, menu se neukáže, protože Steam na Home reaguje sám.
- Ovladač můžeš kdykoli odpojit a znovu připojit, launcher ho najde sám.
- Běží jako uživatelská služba systemd: spustí se po přihlášení, a kdyby spadl, sám se znovu nahodí.

### Ovládání

| Tlačítko | Akce |
|---|---|
| **Home** | otevřít / zavřít menu |
| **◀ ▶** (D-pad nebo levá páčka) | výběr |
| **A** nebo **Start** | spustit |
| **B** | zavřít menu |

**Vypnout** se ptá na potvrzení: první **A** kartu zčervená, druhé **A** PC vypne.

Menu jde ovládat i myší a klávesnicí (šipky, Enter, Esc).

## Požadavky

- Linux se systemd (testováno na Debianu 13, GNOME, Wayland)
- Python 3 s GTK 3 (`python3-gi`, `gir1.2-gtk-3.0`), na většině desktopů už je
- uživatel ve skupině `input`
- Steam (`steam`) a/nebo Heroic jako Flatpak (`com.heroicgameslauncher.hgl`)

Testováno s ovladačem **8BitDo Ultimate 2C Wireless**. Mělo by fungovat s jakýmkoli ovladačem, který posílá tlačítko `BTN_MODE` (Xbox, PlayStation a další).

## Instalace

```bash
git clone https://github.com/knespii/gamepad-launcher.git
```

```bash
cd gamepad-launcher && ./install.sh
```

Pokud nejsi ve skupině `input`:

```bash
sudo usermod -aG input $USER
```

Pak se odhlas a znovu přihlas a spusť `./install.sh` znovu.

## Odinstalace

```bash
./uninstall.sh
```

## Úpravy

Položky menu jsou na začátku souboru `launcher.py` v seznamu `ENTRIES`. Každá má název, ikonu a příkaz. Třeba Lutris přidáš takhle:

```python
{
    "name": "Lutris",
    "icon": "lutris",
    "cmd": ["lutris"],
},
```

Po úpravě spusť znovu `./install.sh`.

### Užitečné příkazy

```bash
systemctl --user status gamepad-launcher
```

```bash
journalctl --user -u gamepad-launcher -f
```

## Nároky na výkon

Prakticky žádné. Program většinu času spí a probudí se jen při stisku tlačítka nebo jednou za 2 s při kontrole nově připojeného ovladače. Zabere asi 45 MB RAM a do her nijak nezasahuje.

## Licence

MIT
