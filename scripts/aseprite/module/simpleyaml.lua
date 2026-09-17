--[[
MIT License

Copyright (c) 2022 Ole Lübke

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
--]]
---@module simpleyaml
local simpleyaml = {}

--- Simple YAML parser which parse only string value wrapped in double quote
---
--- parses the YAML file at `path` to a Lua table
---@param path string Path to yaml file
---@param options { root: string, ordered: boolean } root: pick root key to use only, ordered: make the parsed data ipairs ordered.
---@return table<string, any> table of key:value, `nil` in case of error.
function simpleyaml.parse_file(path, options)
  options = options or {}

  -- helper function to apply function `f(data)` at `nestingLevel` of `tab`
  local function atNestingLevel(nestingLevel, f, data, tab)
    if nestingLevel == 0 then -- arrived at `nestingLevel`, apply `f`
      f(data, tab)
    else -- go deeper recursively
      local key = tab[#tab]
      if type(key) == "table" then
        if #key > 0 then
          atNestingLevel(nestingLevel - 1, f, data, key)
        else
          atNestingLevel(nestingLevel - 1, f, data, key.val)
        end
      end
    end
  end

  -- helper function to insert a new `key` at `nestingLevel` of `tab`
  local function insertKey(key, nestingLevel, tab)
    atNestingLevel(
      nestingLevel,
      function(k, t)
        t[#t + 1] = { key = k, val = {} }
      end,
      key,
      tab
    )
  end

  -- helper function to insert value `str` at `nestingLevel` of `tab`
  local function insertString(str, nestingLevel, tab)
    atNestingLevel(
      nestingLevel,
      function(s, t)
        local key = t[#t]
        if type(key.val) == "table" then
          -- key.val default value is an empty table,
          -- but if the table is inserted as ipairs.
          -- We retrieve the last index and set the last val of it.
          if #key.val > 0 then
            local subkey = key.val[#key.val]
            subkey[#subkey].val = s
          else
            key.val = s
          end
        end
      end,
      str,
      tab
    )
  end

  local function insertList(str, nestingLevel, tab)
    atNestingLevel(
      nestingLevel,
      function(s, t)
        local key = t[#t]
        local n = # (key.val)
        key.val[n + 1] = s
      end,
      str,
      tab
    )
  end

  local function insertListedKey(str, nestingLevel, tab)
    atNestingLevel(
      nestingLevel,
      function(s, t)
        local key = t[#t]
        local n = # (key.val)
        local insert = { key = s, val = {} }
        key.val[n + 1] = { insert }
      end,
      str,
      tab
    )
  end

  -- flatten parsing table by removing indices, so the resulting table can directly be indexed with the YAML keys
  local function flatten(parsed, ordered)
    local flattened = {}

    local function flattenTable(key, value)
      local keyIndex = ordered and #flattened + 1 or key
      local flatPair = ordered and { key = key, val = value } or value
      flattened[keyIndex] = flatPair
    end

    -- for all key-value pairs
    for _, item in ipairs(parsed) do
      if type(item) ~= "table" then
        -- If each members aren't table, it is an array member
        flattened[#flattened + 1] = item
        goto cont_flatten_pair
      end

      if #item > 0 then
        -- ipairs listed items
        flattened[#flattened + 1] = flatten(item, ordered)
      elseif item.key ~= nil then
        -- key-value pair, also need to make sure val is flatten
        if type(item.val) == "table" then
          local value = flatten(item.val, ordered)
          flattenTable(item.key, value)
        else
          flattenTable(item.key, item.val)
        end
      end
      ::cont_flatten_pair::
    end
    return flattened
  end

  local function matchTokens(text, tokens)
    for _, token in ipairs(tokens) do -- for all key-value pairs
      local val = text:match(token)
      if val ~= nil and val:len() > 0 then
        return true
      end
    end
    return false
  end

  -- start parsing

  -- (try to) open YAML file
  local file = io.open(path, "r")
  if not file then
    return nil
  end

  local nestingLevel = 0 -- current nesting level
  local isInsideRoot = true
  local indents      = {} -- stack of indents
  local parsed       = {} -- resulting table

  --- FIXME: we flag some line because we have not implement those yaml feature yet:
  --- A value may be invalid (invalidValue)
  --- which will flag the indents below it (flaggedValue),
  --- keep those flagged until indent is less than it.
  ---@type number | nil
  local invalidValue, flaggedValue

  local function insertValue(line, insertLevel, updates)
    if line ~= nil and line:len() > 0 then
      -- First, find value wrapped in string literal ""
      local value = line:match("^%s*\"(.-)\"%s*$")
      if value ~= nil and value:len() > 0 then
        insertString(value, insertLevel, updates)
        return true
      elseif matchTokens(line, { '~', "^#.*" }) then
        -- '~' are nil value, we can pass this true while not inserting value
        -- "^#.*" Match anything starts with '#' which is comment, we have to ignore.
        return true
      elseif not matchTokens(line, { '|', '>', ">+", "|-" }) then
        -- Else, we can include any value that does NOT match string literal block,
        -- its hard to parse and doesn't fit the scope of simpleyaml.
        insertString(line, insertLevel, updates)
        return true
      else
        -- Else, the value is unsupported, e.g. string literal blocks identifier
        return false
      end
    end
    return nil
  end

  for line in file:lines() do -- for all lines in the file
    -- goto next line if current line is empty, a comment, the document start, or a directive
    if line:gsub("%s*", "") == "" or line:find("^%s*#") ~= nil or line:find("^---") ~= nil or line:find("^%%") ~= nil then
      goto cont_processing_lines
    end

    local indent = line:match("(%s*)%S.*"):len() -- get indent of current line
    if #indents > 0 then -- if stack of indents not empty
      local prevIndent = indents[#indents]

      -- Guard indent lines inside invalidValue,
      -- which will flag as `flaggedValue` until new line has less indent
      if invalidValue ~= nil then
        if flaggedValue ~= nil then
          if indent < flaggedValue then
            flaggedValue = nil
            invalidValue = nil
          else
            goto cont_processing_lines
          end
        end
        -- previous line was marked invalid
        if indents[#indents] == invalidValue then
          -- This line's indent fall inside invalid line
          if indent > invalidValue then
            flaggedValue = indent
            goto cont_processing_lines
          else
            invalidValue = nil
          end
        end
      end

      -- compare with indent of previous line
      if indent > prevIndent then -- if current indent larger, increase nesting level
        nestingLevel = nestingLevel + 1;
      elseif indent < prevIndent then -- of current indent smaller, decrease nesting level and ...
        nestingLevel = nestingLevel - 1;
        while indents[#indents] > indent do -- ... clean up the stack of indents, tracking the nesting level
          if prevIndent < indents[#indents] then
            nestingLevel = nestingLevel + 1
          elseif prevIndent > indents[#indents] then
            nestingLevel = nestingLevel - 1
          end
          prevIndent = indents[#indents]
          table.remove(indents)
        end
      end
    end
    table.insert(indents, indent) -- insert current indent into stack

    -- Try to read line as dash prefixed list first
    local listedKey = line:match("^%s*%-%s(.-):")
    if listedKey ~= nil and listedKey:len() > 0 and isInsideRoot then
      -- Drop 1 nesting level (to the parent) and insert its value (as array/list)
      insertListedKey(listedKey, nestingLevel - 1, parsed)

      -- listed key could have an initial value
      local val = line:match(":%s*(.*)%s*")
      local insert = insertValue(val, nestingLevel - 1, parsed)
      if insert ~= nil then
        invalidValue = not insert and indent or nil
      end
      goto cont_processing_lines
    end

    -- Try to read line as dash prefixed list first
    local list = line:match("^%s*%-%s*\"(.-)\"%s*$")
    if list ~= nil and list:len() > 0 and isInsideRoot then
      -- Drop 1 nesting level (to the parent) and insert its value (as array/list)
      insertList(list, nestingLevel - 1, parsed)
      invalidValue = nil
      goto cont_processing_lines
    end

    -- read rest of the line (everything after the first ':')
    local val = line:match(":%s*(.*)%s*")
    local key

    -- read the key from the line (everything before ':')
    if val ~= nil and val:len() > 0 then
      -- exclude everything after ':' would gives the key
      local replace = val:gsub('([%^%$%(%)%%%.%[%]%*%+%-%q?])', '%%%1')
      key = line:gsub(replace, ""):match("%s*(.*):")
    else
      key = line:match("%s*(.*):")
    end

    if key == "" then -- key is blank? doesn't make sense
      return nil
    elseif key == nil then -- key not matched, could be a comment or blank line
      goto cont_processing_lines
    end

    -- Look for root key at nesting 0
    if options.root ~= nil and nestingLevel == 0 then
      if key == options.root then
        isInsideRoot = true
      else
        isInsideRoot = false
      end
    end

    -- Whitelist keys inside selected root,
    -- or disregard all line inside invalid parent value
    if not isInsideRoot then
      goto cont_processing_lines
    end

    -- insert the key
    insertKey(key, nestingLevel, parsed)

    -- if there is something, insert the rest of the line as a string value
    -- otherwise, the value is an object, so go ahead to read next line
    local insert = insertValue(val, nestingLevel, parsed)
    if insert ~= nil then
      invalidValue = not insert and (indent) or nil
    end

    ::cont_processing_lines::
  end

  file:close()

  result = flatten(parsed, options.ordered)

  if options.root ~= nil then
    if options.ordered then
      -- Need to iterate for root key if the result is ipairs-ordered
      for _, rootKeys in ipairs(result) do
        if rootKeys.key == options.root then
          return rootKeys.val
        end
      end
      return nil
    else
      -- Flatten result with root key
      return result[options.root]
    end
  else
    return result
  end
end

return simpleyaml