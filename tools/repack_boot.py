#!/usr/bin/env python3
"""
Repack boot.img with a new kernel Image.
Usage: python3 repack_boot.py --stock-boot boot.img --kernel Image --output boot_hid.img [--pad-size 32768000]
"""
import struct
import argparse
import os
import sys

def pad_to_page(size, page_size):
    if size % page_size == 0:
        return 0
    return page_size - (size % page_size)

def main():
    parser = argparse.ArgumentParser(description='Repack Android boot.img with a new kernel')
    parser.add_argument('--stock-boot', required=True, help='Path to stock boot.img')
    parser.add_argument('--kernel', required=True, help='Path to new kernel Image')
    parser.add_argument('--output', required=True, help='Output path for repacked boot.img')
    parser.add_argument('--pad-size', type=int, default=0, help='Pad output to this size (0 = no padding)')
    args = parser.parse_args()

    with open(args.stock_boot, 'rb') as f:
        data = f.read()

    magic = data[0:8]
    if magic != b'ANDROID!':
        print(f"ERROR: Not a valid boot.img! Magic: {magic}", file=sys.stderr)
        sys.exit(1)

    kernel_size = struct.unpack('<I', data[8:12])[0]
    kernel_addr = struct.unpack('<I', data[12:16])[0]
    ramdisk_size = struct.unpack('<I', data[16:20])[0]
    second_size = struct.unpack('<I', data[24:28])[0]
    page_size = struct.unpack('<I', data[36:40])[0]
    dt_size = struct.unpack('<I', data[40:44])[0]

    print(f"Stock kernel: {kernel_size} bytes")
    print(f"Ramdisk: {ramdisk_size} bytes")
    print(f"DT: {dt_size} bytes")
    print(f"Page size: {page_size}")

    # Calculate offsets
    ko = page_size
    ro = ko + kernel_size + pad_to_page(kernel_size, page_size)
    so = ro + ramdisk_size + pad_to_page(ramdisk_size, page_size)
    dto = so + second_size + pad_to_page(second_size, page_size)

    # Extract components
    ramdisk = data[ro:ro + ramdisk_size]
    dt_data = data[dto:dto + dt_size] if dt_size > 0 else b''

    # Read new kernel
    with open(args.kernel, 'rb') as f:
        new_kernel = f.read()
    print(f"New kernel: {len(new_kernel)} bytes")

    # Build new header (copy original, update kernel size)
    header = bytearray(data[0:page_size])
    struct.pack_into('<I', header, 8, len(new_kernel))

    # Assemble
    out = bytes(header)
    out += new_kernel + b'\x00' * pad_to_page(len(new_kernel), page_size)
    out += ramdisk + b'\x00' * pad_to_page(ramdisk_size, page_size)
    if second_size > 0:
        out += data[so:so + second_size] + b'\x00' * pad_to_page(second_size, page_size)
    if dt_size > 0:
        out += dt_data + b'\x00' * pad_to_page(dt_size, page_size)

    # Pad to partition size if requested
    if args.pad_size > 0 and len(out) < args.pad_size:
        out += b'\x00' * (args.pad_size - len(out))

    with open(args.output, 'wb') as f:
        f.write(out)

    print(f"\n✅ Repacked: {args.output}")
    print(f"   Size: {len(out)} bytes")
    print(f"   Kernel: {len(new_kernel)} bytes")
    print(f"   Ramdisk: {ramdisk_size} bytes")
    print(f"   DT: {dt_size} bytes")

if __name__ == '__main__':
    main()
