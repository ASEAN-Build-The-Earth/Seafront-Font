-- Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
-- with Reserved Font Name "BTE Seafront".
-- Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
--
-- This Font Software is licensed under the SIL Open Font License, Version 1.1.
-- This license is available with a FAQ at:
-- https://openfontlicense.org

------------------------------------------------------------
-- create-project.lua
--
-- Usage:
-- aseprite --batch --script create-project.lua --script-param dir=src/Basic\ Latin
------------------------------------------------------------

local dir = app.params["dir"]

if not dir then
    error("Missing script parameter: dir")
end

local fontTablePath = dir .. "/font-table.png"
local graphicsPath = dir .. "/regular.png"
local outputPath = dir .. "/design.aseprite"

local tableSprite = app.open(fontTablePath)
local graphicsSprite = app.open(graphicsPath)

local width = tableSprite.width
local height = tableSprite.height
local colorMode = tableSprite.colorMode

local sprite = Sprite(width, height, colorMode)

sprite.filename = outputPath

app.transaction(function()
    sprite:deleteLayer(sprite.layers[1])
end)

------------------------------------------------------------
-- Font Table layer
------------------------------------------------------------

local tableLayer = sprite:newLayer()
tableLayer.name = "Font Table"
tableLayer.isEditable = false

local tableCel = sprite:newCel(
    tableLayer,
    1,
    tableSprite.cels[1].image,
    Point(0, 0)
)

------------------------------------------------------------
-- Graphics layer
------------------------------------------------------------

local graphicsLayer = sprite:newLayer()
graphicsLayer.name = "Regular"

local graphicsCel = sprite:newCel(
    graphicsLayer,
    1,
    graphicsSprite.cels[1].image,
    Point(0, 0)
)

tableSprite:close()
graphicsSprite:close()

------------------------------------------------------------
-- Save
------------------------------------------------------------
function file_exists(name)
   local f=io.open(name,"r")
   if f~=nil then io.close(f) return true else return false end
end

local exists = file_exists(outputPath)

sprite.gridBounds =  Rectangle(0, 0, 64, 64)

local palette = Palette(2)
palette:setColor(0, Color{ r=255, g=255, b=255, a=0 })
palette:setColor(1, Color{ r=0, g=0, b=0, a=255 })
sprite:setPalette(palette)

sprite:saveAs(outputPath)

print((exists and "Overwritten " or "Generated ") .. outputPath)
