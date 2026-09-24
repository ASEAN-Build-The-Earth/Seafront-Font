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
--
-- Optional params:
--   --script-param verbose: Enable verbose logging
------------------------------------------------------------
---@alias Sprite any aseprite [sprite](https://www.aseprite.org/api/sprite) object
---@alias Layer any aseprite [layer](https://www.aseprite.org/api/layer) object
---@alias Cel any aseprite [cel](https://www.aseprite.org/api/cel) object
---@alias Image any aseprite [image](https://www.aseprite.org/api/image) object
---@alias DesignLayers table<number, { style: string, layer: Layer }>

local config = app.params["config"]
local verbose = app.params["verbose"] and true or false

if not config then
    error("Missing script parameter: config")
end

---@type Sprite the active sprite as source
local source = app.sprite

if source == nil then
    error("No sprite opened")
end

local configPath = app.fs.joinPath(config, "font.yml")
local dir = app.fs.filePath(app.sprite.filename)
local designPath = app.fs.joinPath(dir, "design")
local app_filename = app.fs.fileName(app.sprite.filename)
local is_extension = app_filename:match("^ext%-(.+)%.aseprite$") and true or false
local projectsPath = "projects"

simpleyaml = require("module.simpleyaml")
graphics = require("module.graphics")

---@type table<string, any> font.yml parsed config table
local font = simpleyaml.parse_file(configPath, { root="typeface" })

for _, family in ipairs(font.family) do
	---@type DesignLayers design layers of this family
	local layers = graphics.find_design_layers(source, font, family)

	if layers == nil or # (layers) == 0 then
		print("\27[33mWarning (Saves): No graphic layer found for family '" .. family .. "'\27[0m")
		goto cont_save_graphics
	end

	if verbose then
		print("Saving " .. family .. "...")
	end

    for _, design in ipairs(layers) do
		local style = design.style --[[@as number]]
		local graphicsLayer = design.layer --[[@as Layer]]

        -- Export graphicsLayer...
		local out = app.fs.joinPath(designPath, family) --[[@as string]]
		local cel = graphicsLayer:cel(app.activeFrame) --[[@as Cel]]
		local err = nil --[[@as nil|string]]
		local mkdir = app.fs.makeAllDirectories(out)

		if mkdir then
			local mkdirPath = out:match(projectsPath .. "(.*)$") or out
			if verbose then
				print("Using directory: '" .. projectsPath .. mkdirPath .. "'")
			end
		end

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

				if verbose then
					local imagePath = path:match(projectsPath .. "(.*)$") or path
					print("Saved '" .. projectsPath .. imagePath .. "'")
				end
				print("Saved " .. family .. " " .. font.style[style])
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
	::cont_save_graphics::
end