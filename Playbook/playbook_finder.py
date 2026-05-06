#!/usr/bin/env python3
"""
NBA 2K26 Playbook Finder
------------------------
Compares two team dump files and identifies the bytes that differ.
These differences are the playbook data.

Usage:
    python playbook_finder.py dump1.bin dump2.bin
    python playbook_finder.py dump1.bin dump2.bin --show-all
    python playbook_finder.py dump1.bin dump2.bin --output playbook_offsets.json
"""

import sys
import json
import argparse
from pathlib import Path

def compare_dumps(file1, file2, show_all=False):
    """Compare two binary dumps and return differences."""
    data1 = file1.read_bytes()
    data2 = file2.read_bytes()
    
    print(f"File 1: {file1.name} ({len(data1)} bytes)")
    print(f"File 2: {file2.name} ({len(data2)} bytes)")
    print(f"Size difference: {len(data1) - len(data2)} bytes")
    print()
    
    min_len = min(len(data1), len(data2))
    
    # Find all differences
    diffs = []
    for i in range(min_len):
        if data1[i] != data2[i]:
            diffs.append((i, data1[i], data2[i]))
    
    # Add trailing bytes if files differ in size
    if len(data1) != len(data2):
        for i in range(min_len, max(len(data1), len(data2))):
            b1 = data1[i] if i < len(data1) else 0
            b2 = data2[i] if i < len(data2) else 0
            diffs.append((i, b1, b2))
    
    print(f"Total differing bytes: {len(diffs)}")
    
    if not diffs:
        print("Files are identical!")
        return []
    
    # Group differences into contiguous blocks
    blocks = []
    current_block = {"start": diffs[0][0], "end": diffs[0][0], "diffs": [diffs[0]]}
    
    for i in range(1, len(diffs)):
        offset, b1, b2 = diffs[i]
        if offset == current_block["end"] + 1:
            current_block["end"] = offset
            current_block["diffs"].append((offset, b1, b2))
        else:
            blocks.append(current_block)
            current_block = {"start": offset, "end": offset, "diffs": [(offset, b1, b2)]}
    blocks.append(current_block)
    
    print(f"Contiguous difference blocks: {len(blocks)}")
    print()
    
    # Show summary of blocks
    print("Difference blocks:")
    for idx, block in enumerate(blocks):
        print(f"  Block {idx+1}: offset {block['start']} (0x{block['start']:X}) to {block['end']} (0x{block['end']:X}) - {len(block['diffs'])} bytes")
    
    print()
    
    # Show detailed hex dump for each block (limited to first 10 blocks)
    if show_all:
        max_blocks = len(blocks)
    else:
        max_blocks = min(10, len(blocks))
    
    print(f"Detailed hex dump (first {max_blocks} blocks):")
    for idx, block in enumerate(blocks[:max_blocks]):
        print(f"\n  {'='*60}")
        print(f"  Block {idx+1}: offset 0x{block['start']:X} - 0x{block['end']:X} ({len(block['diffs'])} bytes)")
        print(f"  {'='*60}")
        
        # Show hex dump with differences highlighted
        start = block["start"]
        end = block["end"]
        
        # Round down to 16-byte boundary
        dump_start = (start // 16) * 16
        dump_end = ((end // 16) + 1) * 16
        
        for i in range(dump_start, dump_end, 16):
            # File 1 hex
            hex1_parts = []
            hex2_parts = []
            ascii1 = []
            ascii2 = []
            has_diff = False
            
            for j in range(16):
                offset = i + j
                if offset < min_len:
                    b1 = data1[offset]
                    b2 = data2[offset]
                    is_diff = b1 != b2
                    if is_diff:
                        has_diff = True
                    
                    hex1_parts.append(f"{b1:02X}" if not is_diff else f"({b1:02X})")
                    hex2_parts.append(f"{b2:02X}" if not is_diff else f"({b2:02X})")
                    ascii1.append(chr(b1) if 32 <= b1 < 127 else ".")
                    ascii2.append(chr(b2) if 32 <= b2 < 127 else ".")
                else:
                    hex1_parts.append("  ")
                    hex2_parts.append("  ")
                    ascii1.append(" ")
                    ascii2.append(" ")
            
            if has_diff:
                hex1 = " ".join(hex1_parts)
                hex2 = " ".join(hex2_parts)
                a1 = "".join(ascii1)
                a2 = "".join(ascii2)
                print(f"    {i:06X} F1: {hex1}  {a1}")
                print(f"    {i:06X} F2: {hex2}  {a2}")
    
    return diffs

def export_offsets(diffs, output_path):
    """Export difference offsets to JSON."""
    # Group into blocks
    blocks = []
    if diffs:
        current_block = {"start": diffs[0][0], "end": diffs[0][0], "count": 1}
        for i in range(1, len(diffs)):
            offset = diffs[i][0]
            if offset == current_block["end"] + 1:
                current_block["end"] = offset
                current_block["count"] += 1
            else:
                blocks.append(current_block)
                current_block = {"start": offset, "end": offset, "count": 1}
        blocks.append(current_block)
    
    result = {
        "total_diffs": len(diffs),
        "blocks": [
            {
                "offset": b["start"],
                "offset_hex": f"0x{b['start']:X}",
                "size": b["count"],
                "range": f"0x{b['start']:X} - 0x{b['end']:X}",
            }
            for b in blocks
        ]
    }
    
    output_path.write_text(json.dumps(result, indent=2))
    print(f"\nExported offsets to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="NBA 2K26 Playbook Finder")
    parser.add_argument("file1", type=Path, help="First team dump file")
    parser.add_argument("file2", type=Path, help="Second team dump file")
    parser.add_argument("--show-all", action="store_true", help="Show all difference blocks (not just first 10)")
    parser.add_argument("--output", type=Path, default=None, help="Export offsets to JSON file")
    args = parser.parse_args()
    
    if not args.file1.exists():
        print(f"ERROR: {args.file1} not found")
        sys.exit(1)
    if not args.file2.exists():
        print(f"ERROR: {args.file2} not found")
        sys.exit(1)
    
    diffs = compare_dumps(args.file1, args.file2, args.show_all)
    
    if args.output:
        export_offsets(diffs, args.output)

if __name__ == "__main__":
    main()
