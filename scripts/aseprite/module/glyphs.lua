--[[
Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
with Reserved Font Name "BTE Seafront".
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at:
https://openfontlicense.org
--]]
------------------------------------------------------------
-- module glyphs.lua
-- mirrors /seafront/model/glyphs.py: parse_extra_glyphs(dict) -> ExtraGlyphsList
------------------------------------------------------------
---@module glyphs
glyphs = {}

local EXT_PREFIX <const> = "ext-"
local MAX_EXTRA_GLYPHS <const> = 0x100

unicode = require("module.unicode")

--- Get the extra glyph identifier name per index.
---
---@param index number Index (zero based)
---@return string As ext00..ext-FF
function glyphs.getExtraGlyphLabel(index)
    return string.format("%s%02X", EXT_PREFIX, index)
end

--- Parse the given ext-glyphs.yml configuration.
---
---@param extGlyphs table<number, any> parsed yml data of the extra glyphs, must be ordered for ipairs.
---@return table<number, { name: string, cmap: number }> ipairs table of all parsed glyph.
function glyphs.parseExtraGlyphs(extGlyphs)

    local function acceptName(value)
        if type(value) == "string" then
            value = value:match("^%s*(.-)%s*$")

            if value ~= "" then
                return value
            end
        elseif type(value) == "number" then
            return tostring(value)
        end

        return nil
    end


    local function getExtraGlyph(glyph)
        if type(glyph) == "table" and #glyph > 0 then
            -- Ordered table need to extract key:val pairing
            local ext = { name = nil, cmap = nil }
            for _, pair in pairs(glyph) do
                if pair.key == "name" then
                    ext.name = acceptName(pair.val)
                elseif pair.key == "cmap" then
                    ext.cmap = unicode.parseCodepoint(pair.val, function(err)
                        print("WARNING: invalid cmap value for extra glyph.\n" .. err)
                    end)
                end
            end
            return ext
        end

        return { name =  acceptName(glyph), cmap = nil }
    end

    local glyphsYaml = extGlyphs

    if type(glyphsYaml) ~= "table" then
        return {}
    end

    local size = math.min(#glyphsYaml, MAX_EXTRA_GLYPHS)
    local availableIndexes = {} -- Available indexes.
    local glyphsTable = {} -- Result indexed by extra glyph index.
    local unknownKeys = {}

    for i = 0, size - 1 do
        availableIndexes[#availableIndexes + 1] = i
    end

    -- For all 1st level items inside glyph table
    for i, item in ipairs(glyphsYaml) do
        -- # Listed items
        -- glyphs:
        --   - "uni0E01"
        --   - "uni0E0E.short"
        -- # Listed pairs
        -- glyphs:
        --   - name: "uni0E0E.short"
        --     cmap: "U+0E0E"
        if type(item) ~= "table" or #item > 0 then
            local glyph = getExtraGlyph(item)
            if #availableIndexes > 0 then
                glyphsTable[i] = glyph
                table.remove(availableIndexes, 1)
            else
                local key = glyphs.getExtraGlyphLabel(i - 1)
                unknownKeys[#unknownKeys + 1] = { key = key, glyph = glyph }
            end

            -- we can ignore all the table parsing with list
            goto cont_glyphs_item
        end

        -- # Full table form
        -- glyphs:
        --   ext-05: "uni0E0D.less"
        --   some-name:
        --     name: "uni0E0E.short"
        --     cmap: "U+0E0E"
        local key = item.key
        local glyph = getExtraGlyph(item.val)
        local index

        -- Need to validate user defined key name
        if type(key) == "string" then
            local hex = key:match("^ext%-(.+)$")
            if hex then
                index = tonumber(hex, 16)
                if index == nil then
                    print(string.format("WARNING: Extra glyph '%s' has invalid key name", key))
                elseif index >= MAX_EXTRA_GLYPHS then
                    print(string.format("WARNING: Extra glyph '%s' invalid key name: id exceeds FF", key))
                elseif index < 0 then
                    print(string.format("WARNING: Extra glyph '%s' has invalid index", key))
                end
            end
        end

        -- Find index named for this key, is it available?
        if index ~= nil then
            local found
            for j, available in ipairs(availableIndexes) do
                if available == index then
                    table.remove(availableIndexes, j)
                    found = true
                    break
                end
            end

            if found then
                glyphsTable[index + 1] = glyph
            else -- If none found, treat this as an unknown key.
                unknownKeys[#unknownKeys + 1] = { key = key, glyph = glyph }
            end
        else
            -- Not an ext-XX key.
            unknownKeys[#unknownKeys + 1] = { key = key, glyph = glyph }
        end

        ::cont_glyphs_item::
    end

    -- By now, availableIndexes are filled by all valid ext-glyph configurations
    -- For n index that still isn't filled,
    -- we will assign any unknown key (ordered) and log a warning.
    for _, index in ipairs(availableIndexes) do
        if #unknownKeys == 0 then
            break
        end

        local entry = table.remove(unknownKeys)
        local label = glyphs.getExtraGlyphLabel(index)

        print(string.format(
            "WARNING: Extra glyph name key name '%s' labeled as '%s'",
            tostring(entry.key),
            label
        ))

        glyphsTable[index + 1] = entry.glyph
    end

    -- If there's still unknown key(s) after filling all availableIndexes,
    -- Warn about entries that couldn't fit.
    for _, entry in ipairs(unknownKeys) do
        print(string.format(
            "WARNING: Extra glyph '%s' ignored: font table exceeds max size of 256",
            tostring(entry.key)
        ))
    end

    return glyphsTable
end

return glyphs
