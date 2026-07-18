-- Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
-- with Reserved Font Name "BTE Seafront".
-- Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
--
-- This Font Software is licensed under the SIL Open Font License, Version 1.1.
-- This license is available with a FAQ at:
-- https://openfontlicense.org

------------------------------------------------------------
-- export-graphics.lua
--
-- Usage:
--
-- aseprite --batch design.aseprite \
--   --script export-graphics.lua \
--   --script-param output=export.aseprite
------------------------------------------------------------

local output = app.params["output"]

if not output then
    error("Missing output parameter")
end

local source = app.activeSprite

if source == nil then
    error("No sprite opened")
end

------------------------------------------------------------
-- Find Graphics layer
------------------------------------------------------------

local graphicsLayer = nil

for _, layer in ipairs(source.layers) do
    if layer.name == "Regular" then
        graphicsLayer = layer
        break
    end
end

if graphicsLayer == nil then
    error("Graphics \"Regular\" layer not found")
end

local sourceImage = graphicsLayer.cels[1].image
local imageX = graphicsLayer.cels[1].position.x
local imageY = graphicsLayer.cels[1].position.y

------------------------------------------------------------
-- Constants
------------------------------------------------------------

local CELL = 64
local COLUMNS = 16

local rows = math.floor(source.height / CELL)
local glyphCount = rows * COLUMNS
local export = Sprite(CELL, CELL, ColorMode.RGB)
export.filename = output

local layer = export.layers[1]
export:deleteLayer(layer)

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

    local image = Image(CELL, CELL, source.colorMode)

    image:clear(white)

    local x = (i % COLUMNS) * CELL - imageX
    local y = math.floor(i / COLUMNS) * CELL - imageY

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

export:saveAs(output)

print("Generated " .. output)