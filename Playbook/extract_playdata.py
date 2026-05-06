import zipfile, os

path = 'D:\\project\\Playbook\\game files\\playdata.iff'
extract_dir = 'D:\\project\\Playbook\\game files\\playdata_extracted'
os.makedirs(extract_dir, exist_ok=True)

with zipfile.ZipFile(path, 'r') as z:
    z.extractall(extract_dir)
    print('Extracted {} files:'.format(len(z.namelist())))
    for name in z.namelist():
        print('  {} ({} bytes)'.format(name, z.getinfo(name).file_size))
