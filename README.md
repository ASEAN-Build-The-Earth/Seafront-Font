# BuildTheEarth Community Font "Seafront"

A pixelated style typeface developed by the BuildTheEarth Community.

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
--script-param readFile="./src/Basic Latin/sheet.aseprite"  \
--script-param writeFile="./src/Basic Latin/glyphs/glyph.pbm" \
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
usage: export.py [-h] [-v VERBOSE] [-s {base,half,full}] [-a {base,half,full}] [-t {regular,bold,monospace}] [output]

Export a TrueType font from this project

positional arguments:
  output                Output file name *.ttf, default to the psName of exporting typeface.

options:
  -h, --help            show this help message and exit
  -v, --verbose VERBOSE
                        log verbose outputs
  -s, --scale {base,half,full}
                        The scale preset that affect the font's internal positioning. Default to 'base'
  -a, --accent {base,half,full}
                        The accent preset of this font which define the ascent and descend line of this font, Default to 'base'
  -t, --typeface {regular,bold,monospace}
                        Typeface to export configured in config/profile.yml. Default to 'regular'
```