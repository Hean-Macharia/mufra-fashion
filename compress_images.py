#!/usr/bin/env python3
"""
Image Compression Utility for MUFRA FASHIONS
Automatically compresses all product images to improve loading speed
"""

import os
import sys
from pathlib import Path
from PIL import Image
import argparse

def compress_image(image_path, max_width=800, max_height=800, quality=85, optimize=True):
    """
    Compress a single image file
    
    Args:
        image_path (str): Path to the image file
        max_width (int): Maximum width in pixels
        max_height (int): Maximum height in pixels
        quality (int): JPEG quality (1-100, higher = better quality)
        optimize (bool): Whether to optimize the image
        
    Returns:
        tuple: (success, original_size, compressed_size, filename)
    """
    try:
        image_path = Path(image_path)
        
        if not image_path.exists():
            return False, 0, 0, image_path.name
        
        # Get original file size
        original_size = image_path.stat().st_size
        
        # Open and process image
        img = Image.open(image_path)
        
        # Convert RGBA to RGB if saving as JPEG
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Resize image
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Save with compression
        # Determine format from extension
        suffix = image_path.suffix.lower()
        if suffix in ['.jpg', '.jpeg']:
            img.save(image_path, 'JPEG', quality=quality, optimize=optimize)
        elif suffix == '.png':
            img.save(image_path, 'PNG', optimize=optimize)
        elif suffix == '.gif':
            img.save(image_path, 'GIF', optimize=optimize)
        else:
            img.save(image_path, quality=quality, optimize=optimize)
        
        # Get new file size
        compressed_size = image_path.stat().st_size
        
        return True, original_size, compressed_size, image_path.name
        
    except Exception as e:
        print(f"❌ Error processing {image_path}: {str(e)}", file=sys.stderr)
        return False, 0, 0, image_path.name

def main():
    parser = argparse.ArgumentParser(
        description='Compress images in MUFRA FASHIONS uploads folder'
    )
    parser.add_argument(
        '--folder',
        default='static/uploads',
        help='Folder to compress images in (default: static/uploads)'
    )
    parser.add_argument(
        '--width',
        type=int,
        default=800,
        help='Max image width in pixels (default: 800)'
    )
    parser.add_argument(
        '--height',
        type=int,
        default=800,
        help='Max image height in pixels (default: 800)'
    )
    parser.add_argument(
        '--quality',
        type=int,
        default=85,
        help='JPEG quality 1-100 (default: 85)'
    )
    
    args = parser.parse_args()
    
    # Validate folder
    folder = Path(args.folder)
    if not folder.exists():
        print(f"❌ Folder not found: {folder}")
        sys.exit(1)
    
    # Find all images
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    images = []
    
    for ext in image_extensions:
        images.extend(folder.glob(f'*{ext}'))
        images.extend(folder.glob(f'*{ext.upper()}'))
    
    if not images:
        print(f"ℹ️  No images found in {folder}")
        return
    
    print(f"\n🖼️  Found {len(images)} images to compress")
    print(f"📁 Folder: {folder}")
    print(f"⚙️  Settings: {args.width}x{args.height}px, Quality: {args.quality}")
    print("-" * 70)
    
    total_original = 0
    total_compressed = 0
    successful = 0
    failed = 0
    
    # Process each image
    for i, image_path in enumerate(sorted(images), 1):
        success, orig_size, comp_size, filename = compress_image(
            image_path,
            max_width=args.width,
            max_height=args.height,
            quality=args.quality
        )
        
        if success:
            total_original += orig_size
            total_compressed += comp_size
            reduction = ((orig_size - comp_size) / orig_size * 100) if orig_size > 0 else 0
            
            # Format sizes
            orig_mb = orig_size / (1024 * 1024)
            comp_mb = comp_size / (1024 * 1024)
            
            status = "✅" if comp_size < orig_size else "⚠️"
            print(f"{status} [{i:3d}/{len(images)}] {filename:<50} "
                  f"{orig_mb:6.2f}MB → {comp_mb:6.2f}MB ({reduction:5.1f}%)")
            successful += 1
        else:
            print(f"❌ [{i:3d}/{len(images)}] {filename:<50} FAILED")
            failed += 1
    
    # Summary
    total_reduction = ((total_original - total_compressed) / total_original * 100) \
        if total_original > 0 else 0
    
    print("-" * 70)
    print(f"\n📊 Summary:")
    print(f"  ✅ Successfully compressed: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📉 Total reduction: {total_original / (1024*1024):.2f}MB → "
          f"{total_compressed / (1024*1024):.2f}MB ({total_reduction:.1f}%)")
    
    if total_reduction > 0:
        saved = (total_original - total_compressed) / (1024 * 1024)
        print(f"  💾 Space saved: {saved:.2f}MB")
    
    print("\n✅ Image compression complete!\n")

if __name__ == '__main__':
    main()
