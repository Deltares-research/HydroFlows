# Define your list of packages
$packages = @('machow/quartodoc', 'pandoc-ext/section-bibliographies', 'quarto-ext/fontawesome', 'quarto-ext/include-code-files')

# Iterate over the packages
foreach ($package in $packages) {
    # Start the process
    $process = Start-Process quarto -ArgumentList "add", $package -PassThru -Wait -NoNewWindow
}
