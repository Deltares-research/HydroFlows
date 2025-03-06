using Wflow

########## MAIN FUNCTION ##########

# Get the TOML path from CLI
n = length(ARGS)
if n != 1
    throw(ArgumentError(usage))
end
tomlpath = only(ARGS)
if !isfile(tomlpath)
    throw(ArgumentError("File not found: $(tomlpath)\n"))
end

Wflow.run(tomlpath)
