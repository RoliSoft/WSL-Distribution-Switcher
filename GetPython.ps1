function unzip {
    param (
        [string]$archiveFilePath,
        [string]$destinationPath
    )

    if ($archiveFilePath -notlike '?:\*') {
        $archiveFilePath = [System.IO.Path]::Combine($PWD, $archiveFilePath)
    }

    if ($destinationPath -notlike '?:\*') {
        $destinationPath = [System.IO.Path]::Combine($PWD, $destinationPath)
    }

    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem

    $archiveFile = [System.IO.File]::Open($archiveFilePath, [System.IO.FileMode]::Open)
    $archive = [System.IO.Compression.ZipArchive]::new($archiveFile)

    if (Test-Path $destinationPath) {
        foreach ($item in $archive.Entries) {
            $destinationItemPath = [System.IO.Path]::Combine($destinationPath, $item.FullName)

            if ($destinationItemPath -like '*/') {
                New-Item $destinationItemPath -Force -ItemType Directory > $null
            } else {
                New-Item $destinationItemPath -Force -ItemType File > $null

                [System.IO.Compression.ZipFileExtensions]::ExtractToFile($item, $destinationItemPath, $true)
            }
        }
    } else {
        [System.IO.Compression.ZipFileExtensions]::ExtractToDirectory($archive, $destinationPath)
    }
}
Invoke-WebRequest -o python.zip https://www.python.org/ftp/python/3.7.2/python-3.7.2.post1-embed-amd64.zip
unzip python.zip python/
