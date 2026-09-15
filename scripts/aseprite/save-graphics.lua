--[[
Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
with Reserved Font Name "BTE Seafront".
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at:
https://openfontlicense.org
--]]
------------------------------------------------------------
-- save-graphics.lua
--
-- Save all graphics back to image file '{style}.png'
--
-- Usage:
--
-- aseprite --batch "/path/to/projects/{name}/design.aseprite" \
--          --script-param config="/path/to/font/" \
--          --script /path/to/scripts/aseprite/save-graphics.lua
------------------------------------------------------------
---@alias Sprite aseprite [sprite](https://www.aseprite.org/api/sprite) object
---@alias Layer aseprite [layer](https://www.aseprite.org/api/layer) object
---@alias Cel aseprite [cel](https://www.aseprite.org/api/cel) object
---@alias Image aseprite [image](https://www.aseprite.org/api/image) object
---@alias DesignLayers table<number, { "style": string, "layer": Layer }>

local config = app.params["config"]

if not config then
    error("Missing script parameter: config")
end

---@type Sprite the active sprite as source
local source = app.activeSprite

if source == nil then
    error("No sprite opened")
end

local configPath = config .. "/font.yml"
local dir = app.fs.filePath(app.sprite.filename)
local designPath = app.fs.joinPath(dir, "design")
local app_filename = app.fs.fileName(app.sprite.filename)
local is_extension = app_filename:match("^ext%-(.+)%.aseprite$") and true or false

simpleyaml = require("simpleyaml")
graphics = require("graphics")

---@type table<string, ?> font.yml parsed config table
local font = simpleyaml.parse_file(configPath, "typeface")

for _, family in ipairs(font.family) do
	---@type DesignLayers design layers of this family
	local layers = graphics.find_design_layers(source, font, family)

	if layers == nil or # (layers) == 0 then
		error("No graphic layer found for family : " .. family)
	end

	print("Saving " .. family)

    for _, design in ipairs(layers) do
		local style = design.style --[[@as number]]
		local graphicsLayer = design.layer --[[@as Layer]]

        -- Export graphicsLayer...
		local out = app.fs.joinPath(designPath, family) --[[@as string]]
		local cel = graphicsLayer:cel(app.activeFrame) --[[@as Cel]]
		local err = nil --[[@as nil|string]]

		if cel then
			if cel.image then
				local sourceImage = cel.image --[[@as Image]]
				local imageX = cel.position.x --[[@as number]]
				local imageY = cel.position.y --[[@as number]]
				local name = is_extension and ("ext-" .. style) or style
				local path = app.fs.joinPath(out, name .. ".png")
				local image = Image(source.width, source.height, source.colorMode)

				-- Draw the the entire cel (as Image) to the saving .png file
				-- Note: that we must specify the position point to draw at
				-- because the cel image may be smaller than output image
				-- that is position elsewhere (not 0,0)
				image:drawImage(sourceImage, Point(imageX, imageY))
				image:saveAs(path)
				print("Saved '" .. path .. "'")
			else
				err = "Image not found inside graphic layer"
			end
		else
			err = "Cell not found inside graphic layer"
		end

		if err ~= nil then
			error(err .. ': "' .. family .. '/' .. style .. '"')
		end
    end
end