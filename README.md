# BuildTheEarth Community Font "Seafront"

A pixelated style typeface developed by the BuildTheEarth Community.

## Fonts Preview
![BTE-Seafront-Preview](https://github.com/ASEAN-Build-The-Earth/Seafront-Font/blob/main/assets/BTE-Seafront-Preview.png)

## Developer Corner

For devs

### 1. Generate font table for designing graphics
```bash
python generate.py --help
```
```commandline
usage: generate.py [-h] [block]

positional arguments:
  block       Unicode block identifier (default: generate all configured blocks)

options:
  -h, --help  show this help message and exit
```

Unicode blocks are configured in config/project.yml
```yml
blocks:
  - Basic Latin
  - Latin-1 Supplement
  # ...
```

### 2. Export "Graphics" Layer as sprite sheet .aseprite file
```bash
aseprite --batch "./src/Basic Latin/design.aseprite" \
--script-param output="./src/Basic Latin/export.aseprite" \
--script scripts/aseprite/export-graphics.lua 
```

### 3. Export sheet .aseprite (by frames) as spliced .pbm bitmaps.
https://github.com/behreajj/AsePnmIo
```bash
aseprite --batch \
--script-param readFile="./src/Basic Latin/export/Seafront/regular.aseprite"  \
--script-param writeFile="./src/Basic Latin/glyphs/Seafront/regular/glyph.pbm" \
--script-param action=EXPORT \
--script-param writeMode=ASCII \
--script-param frames=ALL \
--script /path/to/netpbmio.lua  
```

### 4. Export TrueType (.ttf) file
```bash
python export.py --help
```
```commandline
usage: export.py [-h] [-v VERBOSE] [-i [IDENTIFIER]] [-s {base,half,full}] [-a {base,half,full}] [-t {regular,monospace,bold}] [-c {Seafront,Seafront Square}] [output]

Export a TrueType font from this project

positional arguments:
  output                Output file name *.ttf, default to the psName of exporting typeface.

options:
  -h, --help            show this help message and exit
  -v, --verbose VERBOSE
                        log verbose outputs
  -i, --identifier [IDENTIFIER]
                        The font's version number to export ex. 1.000
  -s, --scale {base,half,full}
                        The scale preset that affect the font's internal positioning. Default to 'base'
  -a, --accent {base,half,full}
                        The accent preset of this font which define the ascent and descend line of this font, Default to 'base'
  -t, --typeface {regular,monospace,bold}
                        Typeface to export configured in config/font.yml. Default to 'regular'
  -c, --family {Seafront,Seafront Square}
                        The family name to export
```
---
#### Credits
Simple Yaml Parser dependency free:
https://github.com/toolcreator/simpleyaml.lua

Export .aseprite file to pbm bitmap:
https://github.com/behreajj/AsePnmIo
