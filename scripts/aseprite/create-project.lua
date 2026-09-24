--[[
Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
with Reserved Font Name "BTE Seafront".
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at:
https://openfontlicense.org
--]]
------------------------------------------------------------
-- create-project.lua
--
-- Generate or Overwrite the project design file 'design.aseprite'
-- or extension design file 'ext-design.aseprite'.
--
-- Usage:
--
-- aseprite --batch
--          --script-param dir="/path/to/projects/{name}" \
--          --script-param config="/path/to/font/" \
--          --script-param ext="False"|"True",
--          --script /path/to/scripts/aseprite/create-graphics.lua
--
-- Optional params:
--   --script-param verbose: Enable verbose logging
------------------------------------------------------------
---@alias Sprite any aseprite [sprite](https://www.aseprite.org/api/sprite) object
---@alias Layer any aseprite [layer](https://www.aseprite.org/api/layer) object
---@alias Design { style: string, layer: Layer }

local dir = app.params["dir"]
local ext = app.params["ext"]
local config = app.params["config"]
local verbose = app.params["verbose"] and true or false

if not dir then
    error("Missing script parameter: dir")
end
if not config then
    error("Missing script parameter: config")
end

local is_extension = ext and (ext == "True" and true or false) or false
local projectsPath = "projects"
local extParentPath = is_extension and "ext-" or ""
local fontTablePath = app.fs.joinPath(dir, extParentPath .. "font-table.png")
local outputPath = app.fs.joinPath(dir, extParentPath .. "design.aseprite")
local designPath = app.fs.joinPath(dir, "design")
local configPath = app.fs.joinPath(config, "font.yml")

simpleyaml = require("module.simpleyaml")

---@type table<string, any> font.yml parsed config table
local font = simpleyaml.parse_file(configPath, { root="typeface" })

local tableSprite = app.open(fontTablePath)
local width = tableSprite.width
local height = tableSprite.height
local colorMode = tableSprite.colorMode

---@type Sprite new aseprite sprite
local sprite = Sprite(width, height, colorMode)

sprite.filename = outputPath

-- Delete the default background layer
app.transaction(function()
    sprite:deleteLayer(sprite.layers[1])
end)

--- Load all available design images (.png) under a folder
---
---@param folder string The folder path to typeface design to look for
---@return { families:  { name: string, designs: table<number, Design> } }
function loadDesign(folder)
     local typeface = {
        families = {} -- name, designs
    }

    -- For each sub directory in design folder
    for _, familyName in ipairs(app.fs.listFiles(folder)) do
        -- The path name will annotate the font family name
        local directory = app.fs.joinPath(folder, familyName)
        local family = {
            name = familyName, -- string
            designs = {} -- style, path
        }

        if verbose then
            print("Generating to path: " .. directory)
        end

        if not app.fs.isDirectory(directory) then
            print("WARNING: Missing family directory: " .. directory)
        else
            for _, path in ipairs(app.fs.listFiles(directory)) do
                if path:lower():match("%.png$") then
                    local filename = app.fs.fileName(path)
                    local style = not is_extension
                        and filename:gsub("%.png$", "")
                        or filename:match("ext%-(.+)%.png$")
                    local checked = is_extension and true or not style:match("^ext%-")

                    if style and checked then
                        if verbose then
                            print("Found: '"  .. filename ..
                                "' for " .. familyName .. " ".. font.style[style])
                        end
                        table.insert(family.designs, {
                            style = style,
                            path = app.fs.joinPath(directory, path)
                        })
                    end
                end
            end
        end

        table.insert(typeface.families, family)
    end

    return typeface
end


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

local typeface = loadDesign(designPath)
local graphicsGroup = sprite:newGroup()
graphicsGroup.name = "Graphics"

-- We will select only one graphic layer to be visible
local hasPrimaryLayer = false

for _, family in ipairs(typeface.families) do

    -- Family group
    local familyGroup = sprite:newGroup()
    familyGroup.name = family.name
    familyGroup.parent = graphicsGroup


    for _, design in ipairs(family.designs) do

        ---@type Layer Empty design layer
        local designLayer = sprite:newLayer()
        local style = font.style[design.style]
        local isRegular = style == font.style.regular

        designLayer.name = not style and design.style or style
        designLayer.parent = familyGroup

        if not hasPrimaryLayer and isRegular then
            hasPrimaryLayer = true
        else
             designLayer.isVisible = false
        end

        local graphicsSprite = app.open(design.path)
        local designCel = sprite:newCel(
            designLayer,
            1,
            graphicsSprite.cels[1].image,
            Point(0, 0)
        )

        graphicsSprite:close()
    end
end

tableSprite:close()
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

local path = outputPath:match(projectsPath .. "(.*)$") or outputPath
print((exists and "Overwritten \27[33m'" or "Generated \27[33m'") .. projectsPath .. path .. "'\27[0m")
