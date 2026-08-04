--[[
Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
with Reserved Font Name "BTE Seafront".
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at:
https://openfontlicense.org
--]]

local config = app.params["config"]

if not config then
    error("Missing script parameter: config")
end

local source = app.activeSprite

if source == nil then
    error("No sprite opened")
end

local configPath = config .. "/font.yml"
local dir = app.fs.filePath(app.sprite.filename)
local designPath = app.fs.joinPath(dir, "design")

simpleyaml = require("simpleyaml")
graphics = require("graphics")

local font = simpleyaml.parse_file(configPath, "typeface")
for _, family in ipairs(font.family) do
	local layers = graphics.find_design_layers(source, font, family)

	if layers == nil or # (layers) == 0 then
		error("No graphic layer found for family : " .. family)
	end

	print("Saving " .. family)

    for _, design in ipairs(layers) do
		local style = design.style
		local graphicsLayer = design.layer

        -- Export graphicsLayer...
		local out = app.fs.joinPath(designPath, family)
		local cel = graphicsLayer:cel(app.activeFrame)
		local err = nil

		if cel then
			if cel.image then
				local sourceImage = cel.image
				local imageX = cel.position.x
				local imageY = cel.position.y
				local path = app.fs.joinPath(out, style .. ".png")
				local image = Image(source.width, source.height, source.colorMode)

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
			error(
				err .. ': "' ..
				family .. '/' ..
				style .. '"'
			)
		end
    end
end