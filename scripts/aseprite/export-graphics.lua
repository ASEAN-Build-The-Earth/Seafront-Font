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
-- Usage:
--
-- aseprite --batch design.aseprite \
--   --script export-graphics.lua \
--   --script-param output=export.aseprite
------------------------------------------------------------

local config = app.params["config"]

if not config then
    error("Missing script parameter: config")
end

local source = app.activeSprite

if source == nil then
    error("No sprite opened")
end

local app_filename = app.fs.fileName(app.sprite.filename)
local is_extension = app_filename:match("^ext%-(.+)%.aseprite$") and true or false

local configPath = config .. "/font.yml"
local dir = app.fs.filePath(app.sprite.filename)
local exportPath = app.fs.joinPath(dir, "export")

simpleyaml = require("simpleyaml")
graphics = require("graphics")

local font = simpleyaml.parse_file(configPath, nil)

-- print(font.profile.typography["origin-x"] + font.profile.typography["italic-angle"])

local function exportGraphic(design, family)
    local style = design.style
    local graphicsLayer = design.layer

	print("Exporting style: " .. style)

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

    local CELL = 64
    local PBM_CELL = 32

    local rows = math.floor(source.height / CELL)
    local columns = math.floor(source.width / CELL)
    local glyphCount = rows * columns
    local export = Sprite(PBM_CELL, PBM_CELL, ColorMode.RGB)

    export.filename = fileOutput

    local layer = export.layers[1]
    export:deleteLayer(layer) -- Delete default background layer

    local outLayer = export:newLayer()
    outLayer.name = "Glyph"

    local white = Color{ r=255, g=255, b=255, a=255 }

    ------------------------------------------------------------
    -- Generate frames
    ------------------------------------------------------------

    for i = 0, glyphCount - 1 do

        if i > 0 then
            export:newFrame()
        end

        local frame = export.frames[i + 1]
        local image = Image(PBM_CELL, PBM_CELL, source.colorMode)

        image:clear(white)

        local accent = font.profile.accent.base
        local typography = font.profile.typography

        local leftX = PBM_CELL - typography["maximum-width"]
        local cropX = typography["origin-x"] - leftX
        local cropY = typography["origin-y"] + accent["descender"]

        local x = (i % columns) * CELL - imageX + cropX
        local y = math.floor(i / columns) * CELL - imageY + cropY

        image:drawImage(sourceImage, Point(-x, -y))

        export:newCel(
            outLayer,
            frame,
            image,
            Point(0, 0)
        )

    end

    ------------------------------------------------------------
    -- Save
    ------------------------------------------------------------

    export:saveAs(fileOutput)

    print("Generated " .. fileOutput)
end

for _, family in ipairs(font.typeface.family) do
    local layers = graphics.find_design_layers(source, font.typeface, family)

	if layers == nil or # (layers) == 0 then
		error("No graphic layer found for family : " .. family)
	end

	print("Exporting sprite sheet for: " .. family)

    for _, design in ipairs(layers) do
        exportGraphic(design, family)
    end
end