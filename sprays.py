from os.path import getmtime
from pathlib import Path
from sys import stderr

import portalocker
from srctools import VTF
from srctools.vtf import ImageFormats, VTFFlags

lock_path = Path('/var/lock/spray.lock')
lock = portalocker.Lock(lock_path, fail_when_locked=True)
try:
    lock.acquire()
except portalocker.AlreadyLocked as e:
    print(f'[INFO] portalocker.AlreadyLocked: {e}')
    exit()

INPUT_DIRECTORY = Path(r'/in/')
OUTPUT_DIRECTORY = Path(r'/out/')

count = 0

for src_path in INPUT_DIRECTORY.glob('??/????????.dat'):
    if not src_path.is_file():
        continue

    dst_path = OUTPUT_DIRECTORY / (src_path.stem + '.png')

    if not dst_path.exists():
        pass
    elif getmtime(dst_path) < getmtime(src_path):
        pass
    else:
        continue

    try:
        vtf = None
        try:
            with src_path.open('rb') as file:
                try:
                    vtf = VTF.read(file)
                except ValueError as e:
                    print(f'[ERR] {src_path}: {e}', file=stderr)
                    src_path.unlink()
                    continue
                
                if vtf.flags & (VTFFlags.ONEBITALPHA | VTFFlags.EIGHTBITALPHA):
                    if vtf.format == ImageFormats.DXT1:
                        vtf.format = ImageFormats.DXT1_ONEBITALPHA
                    if vtf.low_format == ImageFormats.DXT1:
                        vtf.format = ImageFormats.DXT1_ONEBITALPHA
                    for frame in vtf._frames.values():
                        if frame._fileinfo is not None and frame._fileinfo[2] == ImageFormats.DXT1:
                            frame._fileinfo = (frame._fileinfo[0], frame._fileinfo[1], ImageFormats.DXT1_ONEBITALPHA)

                vtf.load()
        except PermissionError as e:
            print(f'[ERR] {src_path}: {e}', file=stderr)
            continue

        if vtf.frame_count <= 1:
            img = vtf.get().to_PIL()
            img.save(
                dst_path,
                format='PNG',
                optimize=True,
            )
        else:
            img, *imgs = ( vtf.get(frame=index).to_PIL() for index in range(vtf.frame_count) ) 
            img.save(
                dst_path,
                format='PNG',
                optimize=True,
                append_images=imgs,
                save_all=True,
                duration=200,
                loop=0,
            )
        print(f'[INFO] processed \'{src_path}\'')

        count += 1
    except Exception as e:
        print(f'[ERR] {src_path}: {e.with_traceback()}', file=stderr)

print('[INFO] total number of processed files:', count)

lock.release()
