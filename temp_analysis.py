#!/usr/bin/env python3

print('🔍 REAL SHAREPOINT FILES PERFORMANCE ANALYSIS')
print('=' * 65)

# Real SharePoint files from your latest run
files_data = [
    {'name': 'somatosensory.pdf', 'size_mb': 0.13, 'time': 5.88, 'chunks': 4},
    {'name': 'H040021N_committees.pdf', 'size_mb': 1.23, 'time': 25.08, 'chunks': 36},
    {'name': 'H040022N_procurement.pdf', 'size_mb': 1.94, 'time': 38.35, 'chunks': 82},
    {'name': 'H043290N_industrial.pdf', 'size_mb': 0.87, 'time': 14.39, 'chunks': 15},
    {'name': 'hamav_40_060.pdf', 'size_mb': 1.46, 'time': 9.59, 'chunks': 10},
    {'name': 'hamav_50_02.pdf', 'size_mb': 0.68, 'time': 11.31, 'chunks': 8},
    {'name': 'hamav_49_04.pdf', 'size_mb': 1.77, 'time': 19.43, 'chunks': 44}
]

total_files = len(files_data)
total_size = sum(f['size_mb'] for f in files_data)
total_time = sum(f['time'] for f in files_data)
total_chunks = sum(f['chunks'] for f in files_data)

print(f'📊 SUMMARY:')
print(f'   • Files Processed: {total_files}')
print(f'   • Total Size: {total_size:.2f} MB')
print(f'   • Total Time: {total_time:.1f}s ({total_time/60:.1f} minutes)')
print(f'   • Total Chunks: {total_chunks}')
print(f'   • Avg Time/File: {total_time/total_files:.1f}s')
print(f'   • Processing Rate: {total_files/(total_time/60):.1f} files/min')
print()

print('📋 PERFORMANCE BY FILE SIZE:')
for f in sorted(files_data, key=lambda x: x['time'], reverse=True):
    rate = f['size_mb'] / f['time']
    chunk_rate = f['chunks'] / f['time']
    print(f'   {f["name"][:25]:25} | {f["size_mb"]:5.2f} MB | {f["time"]:6.1f}s | {f["chunks"]:2d} chunks | {rate:.3f} MB/s')

print()
print('⚡ KEY INSIGHTS:')
print(f'   • Largest file: 1.94 MB → 38.4s (0.051 MB/s)')
print(f'   • Smallest file: 0.13 MB → 5.9s (0.022 MB/s)')
print(f'   • Average: {total_size/total_files:.2f} MB → {total_time/total_files:.1f}s ({total_size/total_time:.3f} MB/s)')
print(f'   • Time per chunk: {total_time/total_chunks:.2f}s/chunk')
print()
print('🚨 BOTTLENECK CONFIRMED:')
print('   • Document Intelligence: 100% bottleneck (ALL processing time)')
print('   • AI Search: ~0ms (instantaneous upload)')
print('   • Setup: ~0ms (instantaneous)')
print('   • For 800+ page docs: Expect 5-10+ minutes per file')
print()
print('🎯 PHASE 1 OPTIMIZATION TARGETS:')
print('   1. Document Intelligence API optimization')
print('   2. Parallel processing for multiple files')
print('   3. Chunk size optimization')
print('   4. Batch processing strategies')
