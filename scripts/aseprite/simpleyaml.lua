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

local simpleyaml = {}

-- Simple YAML parser which parse only string value wrapped in double quote
-- parses the YAML file at `path` to a Lua table
-- returns `nil` in case of error
function simpleyaml.parse_file(path, root)
  -- helper function to apply function `f(data)` at `nestingLevel` of `tab`
  local function atNestingLevel(nestingLevel, f, data, tab)
    if nestingLevel == 0 then -- arrived at `nestingLevel`, apply `f`
      f(data, tab)
    else -- go deeper recursively
      local key = tab[#tab]
      if key ~= nil then
        atNestingLevel(nestingLevel - 1, f, data, key.val)
      end
    end
  end

  -- helper function to insert a new `key` at `nestingLevel` of `tab`
  local function insertKey(key, nestingLevel, tab)
    atNestingLevel(
      nestingLevel,
      function(k, t)
        if type(t) == "table" then
          table.insert(t, { key = k, val = {} })
        end
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
        if key ~= nil then
          key.val = s
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
        if key ~= nil then
          local n = # (key.val)
          table.insert(key.val, n + 1, s)
        end
      end,
      str,
      tab
    )
  end

  -- flatten parsing table by removing indices, so the resulting table can directly be indexed with the YAML keys
  local function flatten(parsed)
    local flattened = {}
    for _, item in ipairs(parsed) do -- for all key-value pairs
      if type(item) == "string" then -- if each members are string, it is an array object
          local n = # (flattened)
          table.insert(flattened, n + 1, item)
      elseif type(item.val) ~= "string" then -- if the value is not a string (it's a table)
        flattened[item.key] = flatten(item.val) -- flatten the table
      else -- if the value is a string
        flattened[item.key] = item.val -- just assign it
      end
    end
    return flattened
  end

  local function matchUnsupportedToken(text)
    local tokens = {  '|', '>', ">+", "|-", '~' }
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
  local invalidValue = nil

  for line in file:lines() do -- for all lines in the file
    -- goto next line if current line is empty, a comment, the document start, or a directive
    if line:gsub("%s*", "") == "" or line:find("^%s*#") ~= nil or line:find("^---") ~= nil or line:find("^%%") ~= nil then
      goto cont_processing_lines
    end

    local indent = line:match("(%s*)%S.*"):len() -- get indent of current line
    if #indents > 0 then -- if stack of indents not empty
      local prevIndent = indents[#indents]

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
    local list = line:match("^%s*%-%s*\"(.-)\"%s*$")
    if list ~= nil and list:len() > 0 and isInsideRoot and nestingLevel ~= invalidValue then
      -- Drop 1 nesting level (to the parent) and insert its value (as array/list)
      insertList(list, nestingLevel - 1, parsed)
      invalidValue = nil
      goto cont_processing_lines
    end

    -- read rest of the line (everything after the first ':')
    local val = line:match(":%s*(.*)%s*")
    local key = nil

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

    if root ~= nil and nestingLevel == 0 then
      if key == root then
        isInsideRoot = true
      else
        isInsideRoot = false
      end
    end

    -- Whitelist keys inside selected root,
    -- or disregard all line inside invalid parent value
    if not isInsideRoot or nestingLevel == invalidValue then
      goto cont_processing_lines
    end

    -- insert the key
    insertKey(key, nestingLevel, parsed)

    -- if there is something, insert the rest of the line as a string value
    -- otherwise, the value is an object, so go ahead to read next line
    line = val
    if line ~= nil and line:len() > 0 then
      -- Find value wrapped in string literal "" only
      local value = line:match("^%s*\"(.-)\"%s*$")

      if value ~= nil and value:len() > 0 then
        insertString(value, nestingLevel, parsed)
        invalidValue = nil
      elseif not matchUnsupportedToken(line) then -- ignore string literal blocks, we dont support it yet
        insertString(line, nestingLevel, parsed)
        invalidValue = nil
      else
        invalidValue = nestingLevel + 1
        -- print("WARNING: value '" .. line .. "' not wrapped in quote. the key '" .. key .. "' will be ignored")
      end
    end

    ::cont_processing_lines::
  end

  file:close()

  result = flatten(parsed)

  if root ~= nil then
    return result[root]
  else
    return result
  end
end

return simpleyaml