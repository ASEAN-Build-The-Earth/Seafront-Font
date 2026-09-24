--[[
Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
with Reserved Font Name "BTE Seafront".
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at:
https://openfontlicense.org
--]]
---@module graphics
graphics = {}

---@alias Sprite any aseprite [sprite](https://www.aseprite.org/api/sprite) object
---@alias Layer any aseprite [layer](https://www.aseprite.org/api/layer) object
---@alias Font table<string, any> font.yml parsed config table
---@alias DesignLayers table<number, { style: string, layer: Layer }>
---@alias Image any aseprite [image](https://www.aseprite.org/api/image) object

--- Find design layer(s) of a font family name within source sprite.
---
---@param source Sprite aseprite source to find design layer.
---@param font Font font.yml config table.
---@param familyName string Family name of the design to find.
---@return DesignLayers Table of all found layer.
function graphics.find_design_layers(source, font, familyName)
	local function collectDesignLayers(familyGroup)
		---@type DesignLayers
		layers = {} -- list of layers

		for _, layer in ipairs(familyGroup.layers) do
			for style in pairs(font.style) do
				if layer.name == font.style[style] then
					local n = # (layers)
					table.insert(layers, n + 1, { style=style, layer=layer })
				end
			end
		end

		return layers
	end

    for _, group in ipairs(source.layers) do
		-- Look for grouped layer named "Graphics"
		if group.name == "Graphics" and group.isGroup then
			-- Look for each family inside graphics group
    		for _, familyGroup in ipairs(group.layers) do
				if familyGroup.name == familyName and familyGroup.isGroup then
					return collectDesignLayers(familyGroup)
				end
			end
		end
    end

    return nil
end

--- Save aseprite Image as a simple .pbm ASCII 0/1 bitmap
---
---@param black number Which integer color value is the black pixel (Written '1' in pbm file)
---@param image Image The aseprite Image object, used image:getPixel(x, y)
---@param path string Export path of the pbm file
---@return void
function graphics.savePBM(black, image, path)
    local file = io.open(path, "w+")
	if file == nil then
		error("Failed to open PBM file for writing at: " .. path)
	end
    file:write("P1\n")
    file:write(image.width .. " " .. image.height .. "\n")

    for y = 0, image.height - 1 do
        for x = 0, image.width - 1 do
            local pixel = image:getPixel(x, y)
			local value = pixel == black and "1" or "0"

            if x > 0 then
                file:write(" ")
            end
            file:write(value)
        end
        file:write("\n")
    end

    file:close()
end

return graphics
