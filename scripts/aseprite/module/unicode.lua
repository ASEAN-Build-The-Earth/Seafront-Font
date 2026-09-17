--[[
Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
with Reserved Font Name "BTE Seafront".
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at:
https://openfontlicense.org
--]]
------------------------------------------------------------
-- module unicode.lua
-- mirrors /seafront/unicode.py: parse_codepoint(value) -> int
------------------------------------------------------------
---@module unicode
unicode = {}

--- Parse string or integer value as unicode hex decimal codepoint
---
---@param value any Value to parse as unicode codepoint integer
---@param errorFunc fun(error:string):void Error function called when the value cannot be parsed.
---@return number | nil Codepoint integer as number, or nil if the value cannot be parsed.
function unicode.parseCodepoint(value, errorFunc)
    --- Matches:
    --- * \uXXXX
    --- * U+XXXX / U+XXXXXX
    --- * uniXXXX / uniXXXXXX
    --- * 0xXXXX / 0xXXXXXX
    --- * Plain hexadecimal XXXX / XXXXXX
    ---@type table<number, string>
    local PATTERNS <const> = {
        "^\\u([0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f])$",
        "^[Uu]%+([0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]?[0-9A-Fa-f]?)$",
        "^[Uu][Nn][Ii]([0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]?[0-9A-Fa-f]?)$",
        "^0[xX]([0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]?[0-9A-Fa-f]?[0-9A-Fa-f]?)$",
        "^([0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]?[0-9A-Fa-f]?)$"
    }

    ---@type number
    local codepoint

    if type(value) == "boolean" then
        errorFunc("Boolean is not a Unicode code point")
        return nil
    elseif type(value) == "number" then
        -- Make sure integers are actually integers.
        if value ~= math.floor(value) then
            errorFunc("Unicode code point must be an integer, got " .. tostring(value))
            return nil
        end
        codepoint = value
    elseif type(value) == "string" then
        ---@type string
        local unicodeString = value:match("^%s*(.-)%s*$")

        if unicodeString == "" then
            errorFunc("Invalid Unicode code point: empty string")
            return nil
        end

        for _, pattern in ipairs(PATTERNS) do
            local hexString = unicodeString:match(pattern)
            if hexString then
                codepoint = tonumber(hexString, 16)
                break
            end
        end

        if not codepoint then
            errorFunc("Invalid Unicode code point: " .. tostring(value))
            return nil
        end
    else
        errorFunc("Expected number or string for Unicode code point, got " .. type(value))
        return nil
    end
    -- 0x0000..0x10FFFF
    if codepoint < 0 or codepoint > 0x10FFFF then
        errorFunc(string.format(
        "Unicode code point out of range: 0x%X (must be 0x0000..0x10FFFF)", codepoint))
        return nil
    end
    -- Unicode surrogate code points
    if codepoint >= 0xD800 and codepoint <= 0xDFFF then
        errorFunc(string.format(
        "Unicode surrogate is not a valid scalar value: 0x%X", codepoint))
        return nil
    end

    return codepoint
end

return unicode
