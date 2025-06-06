The simple multiplayer 2D tanks game in Python, developed with my kids.  

![tanks](tanks.png)

#### FEATURES
- gameplay resembles famous NES game Battle City
- allow multiple players to fight each other via network  
  tested on local home network, but theoretically may work via Internet (didn't tested, though)
- game is compatible with [RetroPy](https://github.com/WiseToad/RetroPy) libretro core

#### COMPATIBILITY
- developed with Python 3.11.2  
  It's a pity that Debian Bookworm and Raspi OS are delaying to get to Py 12+ so my generics are not so nice in the code as I would wish

#### REQUIREMENTS
Python modules:
- pygame
- configobj

To meet these requirements do either `pip install ...` (Windows and so) or `apt install python3-...` (Ubuntu and so)

#### CONFIGURE
See tanks.conf
        
#### USAGE
- cd src/
- run `server.py` once on some machine reachable for all clients via network
- run `tanks.py` for each client that desires to play

#### CONTROLS
Keyboard:
- arrow keys - move
- `Space`, `Right Ctrl` - shoot
- `PgUp`, `PgDn` - cycle maps

Joypad:
- `D-Pad` - move
- `A` - shoot
- `Select`+`D-Pad` - cycle maps
- `Select` (on release) - cycle map forward 

#### TODO
- fix sudden crashes (due to short-term connectivity lost?)
- allow two players to play on same client (needed especially for libretro cores)
- implement bonuses appearing randomly on map - health, rapid fire, velocity boost, vulnerability, etc
- test map cycling with joypads
- design more maps
