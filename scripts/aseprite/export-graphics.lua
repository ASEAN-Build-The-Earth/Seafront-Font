--[[
Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
with Reserved Font Name "BTE Seafront".
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at:
https://openfontlicense.org
--]]
------------------------------------------------------------
-- export-graphics.lua
--
-- Export graphic layers inside design file 'design.aseprite',
-- as sprite frame ordered cell indexes 'export.aseprite'
--
-- Usage:
--
-- aseprite --batch "/path/to/projects/{name}/design.aseprite" \
--          --script-param config="/path/to/font/" \
--          --script-param codepoint="0E00" \
--          --script /path/to/scripts/aseprite/export-graphics.lua
--
-- Optional params:
--   --script-param verbose: Enable verbose logging
--   --script-param debug: Export debugging .aseprite file under /export
------------------------------------------------------------
---@alias Sprite any aseprite [sprite](https://www.aseprite.org/api/sprite) object
---@alias Layer any aseprite [layer](https://www.aseprite.org/api/layer) object
---@alias DesignLayers table<number, { style: string, layer: Layer }>

local config = app.params["config"]
local start0 = app.params["codepoint"]
local verbose = app.params["verbose"] and true or false
local generateFile = app.params["debug"] and true or false
local app_filename = app.fs.fileName(app.sprite.filename)
local is_extension = app_filename:match("^ext%-(.+)%.aseprite$") and true or false

local codepoint = nil

simpleyaml = require("module.simpleyaml")
graphics = require("module.graphics")
unicode = require("module.unicode")
glyphs = require("module.glyphs")

if not is_extension then
    if not start0 then
        error("Missing script parameter: codepoint")
    end

    codepoint = unicode.parseCodepoint(start0, function(err)
        error("Script parameter: codepoint, invalid value.\n" .. err)
    end)
    if not codepoint then
        error("Script parameter: codepoint, not a valid hex number.")
    end
end

if not config then
    error("Missing script parameter: config")
end

---@type Sprite the active sprite as source
local source = app.sprite

if source == nil then
    error("Aseprite file has no sprite opened")
end

local configPath = app.fs.joinPath(config, "font.yml")
local dir = app.fs.filePath(app.sprite.filename)
local exportPath = app.fs.joinPath(dir, "export")
local glyphsPath = app.fs.joinPath(dir, "glyphs")
local extGlyphsYML = app.fs.joinPath(dir, "profile", "ext-glyphs.yml")
local projectsPath = "projects"

---@type table<string, any> font.yml parsed config table
local font = simpleyaml.parse_file(configPath, nil)

local extGlyphs = nil
if is_extension then
    local rawGlyph = simpleyaml.parse_file(extGlyphsYML, {  root="glyphs", ordered=true })
    extGlyphs = glyphs.parseExtraGlyphs(rawGlyph)
    if extGlyphs == nil then
        error("Extra glyph definition profile required to export: " .. extGlyphsYML)
    end
end

--- Export design layer of a font family ordered by all cels to sprite frames.
--- Export file are under /export/{family}/{style}.aseprite
---
---@param design { style: string, layer: Layer } Design layer information
---@param family string The family name of this graphics layer
local function exportGraphic(design, family)
    local style = design.style
    local graphicsLayer = design.layer

    if verbose then
	    print("Exporting style: " .. style)
    end

    local out = app.fs.joinPath(exportPath, family)
    local cel = graphicsLayer.cels[1]

    local sourceImage = cel.image
    local imageX = cel.position.x
    local imageY = cel.position.y

    ------------------------------------------------------------
    -- Constants
    ------------------------------------------------------------
    local name = is_extension and ("ext-" .. style) or style
    local fileOutput = app.fs.joinPath(out, name .. ".aseprite")
    local glyphFolder = app.fs.joinPath(glyphsPath, family, name)
    local mkDirResult = app.fs.makeAllDirectories(glyphFolder)

    if verbose and mkDirResult then
        local mkdirPath = glyphFolder:match(projectsPath .. "(.*)$") or glyphFolder
        print("Using directory: '" .. projectsPath .. mkdirPath .. "'")
    end

    local CELL = 64
    local PBM_CELL = 32

    local rows = math.floor(source.height / CELL)
    local columns = math.floor(source.width / CELL)
    local glyphCount = rows * columns
    local export = Sprite(PBM_CELL, PBM_CELL, ColorMode.INDEXED)
    local palette = Palette(3)

    palette:setColor(2, Color{ r=255, g=255, b=255, a=255 })
    palette:setColor(1, Color{ r=0, g=0, b=0, a=255 })
    palette:setColor(0, Color{ r=0, g=0, b=0, a=0 })
    export:setPalette(palette)

    export.filename = fileOutput

    local layer = export.layers[1]
    layer:cel().image:clear(2)
    local outLayer = export:newLayer()
    outLayer.name = "Glyph"
    export.transparentColor = 0
    ------------------------------------------------------------
    -- Generate frames
    ------------------------------------------------------------

    local built = 0
    for i = 0, glyphCount - 1 do

        if i > 0 then
            export:newFrame()
        end

        local frame = export.frames[i + 1]
        local image = Image(PBM_CELL, PBM_CELL, ColorMode.INDEXED)

        local accent = font.profile.accent.base
        local typography = font.profile.typography

        local leftX = PBM_CELL - typography["maximum-width"]
        local cropX = typography["origin-x"] - leftX
        local cropY = typography["origin-y"] + accent["descender"]

        local x = (i % columns) * CELL - imageX + cropX
        local y = math.floor(i / columns) * CELL - imageY + cropY

        image:drawImage(sourceImage, Point(-x, -y))

        if not image:isEmpty() then

            if is_extension then
                local profile = extGlyphs[i + 1]
                local extName
                if profile.name ~= nil then
                    extName = profile.name .. ".pbm"
                elseif profile.cmap ~= nil then
                    extName = string.format("uni%04X.pbm", profile.cmap)
                else
                    extName = glyphs.getExtraGlyphLabel(i)
                    print("\27[33mWARNING: Extra glyph '" .. extName .. "' has no configured name.\27[0m")
                end
                local pbm_file = app.fs.joinPath(glyphFolder, extName)

                graphics.savePBM(1, image, pbm_file)
                built = built + 1
                if verbose then
                    extName = glyphs.getExtraGlyphLabel(i)
                    print("Wrote (" .. extName .. "): " .. pbm_file)
                end
            else
                local glyph_unicode = codepoint + i
                local glyph_name = string.format("uni%04X.pbm", glyph_unicode)
                local pbm_file = app.fs.joinPath(glyphFolder, glyph_name)

                graphics.savePBM(1, image, pbm_file)
                built = built + 1
                if verbose then
                    print("Wrote: (" .. string.format(
                        "U+%04X", glyph_unicode) .. "): " .. pbm_file)
                end
            end


        elseif verbose then
            if codepoint ~= nil then
                print("Skipped " .. string.format(
                    "U+%04X", codepoint + i) .. " (Empty)")
            else
                print("Skipped cell [" .. i .. "] (Empty)")
            end
        end

        export:newCel(outLayer, frame, image, Point(0, 0))
    end

    ------------------------------------------------------------
    -- Save
    ------------------------------------------------------------
    print("Wrote " .. built .. " files for " .. family .. " " .. font.typeface.style[style])

    if generateFile then
        export:saveAs(fileOutput)

        local exportedPath = fileOutput:match(projectsPath .. "(.*)$") or fileOutput
        print("Generated '" .. projectsPath .. exportedPath .. "'")
    end
end

for _, family in ipairs(font.typeface.family) do
	---@type DesignLayers design layers of this family
    local layers = graphics.find_design_layers(source, font.typeface, family)

	if layers == nil or # (layers) == 0 then
		print("\27[33mWarning: No graphic layer found for family '" .. family .. "'\27[0m")
	else
        if verbose then
            print("Exporter family: " .. family)
        end
        for _, design in ipairs(layers) do
            exportGraphic(design, family)
        end
    end
end