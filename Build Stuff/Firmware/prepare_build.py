"""Prepare a Linux build copy of editable source; no flashing/network access."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess


def prepare(destination):
    base=Path(__file__).resolve().parent
    destination=Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError('Build destination must be empty; existing files will not be overwritten')
    if ' ' in str(destination):
        raise RuntimeError('ESP-IDF build paths must not contain spaces')
    destination.mkdir(parents=True,exist_ok=True)
    lock=json.loads((base/'source-lock.json').read_text(encoding='utf-8'))
    for name in ['MicroPython','Camera-API','ESP-IDF','mp_jpeg','Managed']:
        shutil.copytree(base/'Sources'/name,destination/name,
                        ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc'))

    # The generic S3 profile defaults to a 4 MB flash header even when its
    # SPIRAM_OCT variant is selected. This board is N16R8: retain the upstream
    # octal-PSRAM settings and flexible filesystem layout, but explicitly
    # select 16 MB flash in this disposable build copy.
    board=destination/'MicroPython/ports/esp32/boards/ESP32_GENERIC_S3'
    variant=board/'mpconfigvariant_SPIRAM_OCT.cmake'
    with variant.open('a',encoding='utf-8') as output:
        output.write('\n# BSHE27 GOOUUU N16R8 flash size.\n'
                     'list(APPEND SDKCONFIG_DEFAULTS\n'
                     '    boards/ESP32_GENERIC_S3/sdkconfig.bshe27_n16r8\n)\n')
    (board/'sdkconfig.bshe27_n16r8').write_text(
        '# Generic S3 base selects 4 MB; override only the flash capacity.\n'
        '# CONFIG_ESPTOOLPY_FLASHSIZE_4MB is not set\n'
        'CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y\n',encoding='utf-8')
    for link in lock.get('source_links',[]):
        relative=Path(link['path']).relative_to('Sources')
        if relative.parts[0]=='Installed-MicroPython':
            continue
        target=(destination/relative).resolve()
        if not target.is_relative_to(destination):
            raise RuntimeError('Unsafe source link')
        if target.is_file() or target.is_symlink():
            target.unlink()
        elif target.exists():
            raise RuntimeError('Refusing to replace a populated source directory with a link')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.symlink_to(link['target'])

    # Create local version metadata in the disposable copy only. Upstream
    # snapshots have no nested .git directory; source edits are carried across.
    for name,tag in [('MicroPython','v1.27.0'),('ESP-IDF','v5.5.1')]:
        folder=destination/name
        subprocess.run(['git','init','-q',str(folder)],check=True)
        subprocess.run(['git','-C',str(folder),'add','-A'],check=True)
        subprocess.run(['git','-C',str(folder),'-c','commit.gpgsign=false','-c','user.name=BSHE27 local build',
                        '-c','user.email=bshe27@localhost','commit','-qm','Editable local firmware source snapshot'],check=True)
        subprocess.run(['git','-C',str(folder),'-c','tag.gpgsign=false','tag',tag],check=True)

    def manifest(relative,dependencies):
        # JSON is also valid YAML. Use local, pinned managed component copies.
        (destination/relative).write_text(json.dumps({'dependencies':dependencies},indent=2)+'\n',encoding='utf-8')
    jpeg={'override_path':str(destination/'Managed/esp_new_jpeg')}
    manifest('MicroPython/ports/esp32/main/idf_component.yml',{
        'espressif/mdns':{'override_path':str(destination/'Managed/mdns')},
        'espressif/tinyusb':{'override_path':str(destination/'Managed/tinyusb')},
        'idf':{'version':'>=5.2.0'}})
    manifest('Camera-API/idf_component.yml',{
        'espressif/esp32-camera':{'override_path':str(destination/'Camera-API/esp32-camera')},
        'espressif/esp_new_jpeg':jpeg,'idf':{'version':'>=5.2.0'}})
    manifest('mp_jpeg/idf_component.yml',{'espressif/esp_new_jpeg':jpeg,'idf':{'version':'>=5.0.0'}})
    print('Prepared camera-target MicroPython with explicit local component overrides')
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',help='New/empty Linux directory without spaces')
    args=parser.parse_args()
    prepare(args.destination)
