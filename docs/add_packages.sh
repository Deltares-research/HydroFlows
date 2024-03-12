#!/usr/bin/expect -f

# Define your list of packages
set packages {machow/quartodoc pandoc-ext/section-bibliographies quarto-ext/fontawesome quarto-ext/include-code-files}

# Iterate over the packages
foreach package $packages {
    spawn quarto add $package
    expect "Do you trust the authors of this extension"
    send -- "y\r"
    expect "Would you like to continue"
    send -- "y\r"
    expect eof
}
