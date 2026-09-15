--[[
Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
with Reserved Font Name "BTE Seafront".
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at:
https://openfontlicense.org
--]]
---@module 'graphics'
graphics = {}

---@alias Sprite aseprite [sprite](https://www.aseprite.org/api/sprite) object
---@alias Layer aseprite [layer](https://www.aseprite.org/api/layer) object
---@alias Font table<string, ?> font.yml parsed config table
---@alias DesignLayers table<number, { "style": string, "layer": Layer }>

--- Find design layer(s) of a font family name within source sprite.
---
---@param source Sprite aseprite source to find design layer.
---@param font font.yml config table.
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

return graphics