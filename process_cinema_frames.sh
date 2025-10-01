#!/bin/bash

# Cinema Frame Processing Script
# Converts PNG frame sequences to MP4 videos and optionally concatenates them
# Usage: ./process_cinema_frames.sh [options]

set -e  # Exit on any error

# Default configuration
FRAMERATE=10
CRF=18
PRESET="medium"
PIX_FMT="yuv420p"
QUALITY="good"
SCALE=""
INTERPOLATE=false
TARGET_FPS=""
CONCAT=true
OUTPUT_DIR=""
CLEANUP=true
SPEED=1.0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Help function
show_help() {
    cat << EOF
Cinema Frame Processing Script

USAGE:
    $0 [OPTIONS] [CINEMA_DIR]

ARGUMENTS:
    CINEMA_DIR          Path to frames directory (default: prompt for directory and version)

OPTIONS:
    -f, --framerate     Input framerate (default: 10)
    -c, --crf           Constant Rate Factor for quality (default: 18)
    -p, --preset        x264 preset (default: medium)
    -q, --quality       Quality preset: good, smaller, poor, terrible, prores, 4k (default: good)
    -s, --scale         Scale filter (e.g., "3840:-2" for 4K)
    -i, --interpolate   Enable frame interpolation
    -t, --target-fps    Target FPS for interpolation (e.g., 30)
    --no-concat         Skip concatenation step
    -o, --output        Output directory (default: same as input)
    --speed             Speed multiplier for final video (e.g., 2.0 for 2x speed)
    --no-cleanup        Keep intermediate files after processing
    -h, --help          Show this help

EXAMPLES:
    # Basic processing with 10fps
    $0

    # High quality with 4K scaling
    $0 --quality 4k

    # Frame interpolation to 30fps
    $0 --interpolate --target-fps 30

    # Smaller files, no concatenation, keep intermediate files
    $0 --quality smaller --no-concat --no-cleanup

    # Custom framerate and CRF
    $0 --framerate 20 --crf 20

    # Speed up final video 2x
    $0 --speed 2.0

    # Poor quality for small files
    $0 --quality poor

    # Terrible quality for tiny files
    $0 --quality terrible

QUALITY PRESETS:
    good      - CRF 18, medium preset (visually lossless)
    smaller   - CRF 23, fast preset (smaller files)
    poor      - CRF 32, ultrafast preset, 960p (very small files)
    terrible  - CRF 35, ultrafast preset, 640p (tiny files)
    prores    - ProRes 422 HQ for editing
    4k        - 4K delivery with CRF 20, slow preset
EOF
}

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--framerate)
            FRAMERATE="$2"
            shift 2
            ;;
        -c|--crf)
            CRF="$2"
            shift 2
            ;;
        -p|--preset)
            PRESET="$2"
            shift 2
            ;;
        -q|--quality)
            QUALITY="$2"
            shift 2
            ;;
        -s|--scale)
            SCALE="$2"
            shift 2
            ;;
        -i|--interpolate)
            INTERPOLATE=true
            shift
            ;;
        -t|--target-fps)
            TARGET_FPS="$2"
            shift 2
            ;;
        --no-concat)
            CONCAT=false
            shift
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --speed)
            SPEED="$2"
            shift 2
            ;;
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            log_error "Unknown option $1"
            show_help
            exit 1
            ;;
        *)
            CINEMA_DIR="$1"
            shift
            ;;
    esac
done

# Apply quality presets
case $QUALITY in
    good)
        CRF=18
        PRESET="medium"
        ;;
    smaller)
        CRF=23
        PRESET="fast"
        ;;
    poor)
        CRF=32
        PRESET="ultrafast"
        SCALE="960:-2"
        ;;
    terrible)
        CRF=35
        PRESET="ultrafast"
        SCALE="640:-2"
        ;;
    prores)
        CRF=""
        PRESET=""
        PIX_FMT="yuv422p10le"
        ;;
    4k)
        CRF=20
        PRESET="slow"
        SCALE="3840:-2"
        ;;
    *)
        log_warning "Unknown quality preset: $QUALITY. Using custom settings."
        ;;
esac

# Get user input for directory and version if not provided
if [[ -z "$CINEMA_DIR" ]]; then
    echo ""
    log_info "Cinema frame processing requires directory and version input."
    echo ""
    
    # Get output directory
    read -p "Enter output directory (e.g., cinema_test): " OUTPUT_BASE_DIR
    if [[ -z "$OUTPUT_BASE_DIR" ]]; then
        log_error "Output directory is required"
        exit 1
    fi
    
    # Get version
    read -p "Enter version (e.g., 4346): " VERSION
    if [[ -z "$VERSION" ]]; then
        log_error "Version is required"
        exit 1
    fi
    
    # Construct frames directory path
    CINEMA_DIR="$OUTPUT_BASE_DIR/$VERSION/frames"
    
    if [[ ! -d "$CINEMA_DIR" ]]; then
        log_error "Frames directory does not exist: $CINEMA_DIR"
        log_info "Expected structure: <output directory>/<version>/frames/"
        log_info "Example: cinema_test/4346/frames/"
        exit 1
    fi
    
    log_success "Using frames directory: $CINEMA_DIR"
fi

# Resolve path (handle spaces properly)
CINEMA_DIR=$(realpath "$CINEMA_DIR" 2>/dev/null || echo "$CINEMA_DIR")

if [[ ! -d "$CINEMA_DIR" ]]; then
    log_error "Cinema directory does not exist: $CINEMA_DIR"
    exit 1
fi

# Set output directory
if [[ -z "$OUTPUT_DIR" ]]; then
    # Default to .fle/videos in the project directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    OUTPUT_DIR="$SCRIPT_DIR/.fle/videos"
    mkdir -p "$OUTPUT_DIR"
fi

log_info "Processing cinema frames from: $CINEMA_DIR"
log_info "Output directory: $OUTPUT_DIR"
log_info "Framerate: $FRAMERATE fps"
log_info "Quality: $QUALITY (CRF: $CRF, Preset: $PRESET)"

# Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    log_error "ffmpeg is required but not installed. Please install it first."
    exit 1
fi

# Find all batch directories
BATCH_DIRS=()
while IFS= read -r dir; do
    BATCH_DIRS+=("$dir")
done < <(find "$CINEMA_DIR" -type d -name "batch_*" | sort)
if [[ ${#BATCH_DIRS[@]} -eq 0 ]]; then
    log_error "No batch directories found in $CINEMA_DIR"
    exit 1
fi

log_info "Found ${#BATCH_DIRS[@]} batch directories"

# Process each batch directory
PROCESSED_MP4S=()
for batch_dir in "${BATCH_DIRS[@]}"; do
    batch_name=$(basename "$batch_dir")
    log_info "Processing $batch_name..."
    
    # Check if PNG files exist
    png_count=$(find "$batch_dir" -name "*.png" | wc -l)
    if [[ $png_count -eq 0 ]]; then
        log_warning "No PNG files found in $batch_dir, skipping..."
        continue
    fi
    
    # Determine output filename
    output_mp4="$OUTPUT_DIR/${batch_name}.mp4"
    
    # Build ffmpeg command
    ffmpeg_cmd="ffmpeg -y -framerate $FRAMERATE -i \"$batch_dir/%06d.png\""
    
    # Add video filters
    video_filters=()
    
    if [[ "$INTERPOLATE" == true ]]; then
        if [[ -n "$TARGET_FPS" ]]; then
            video_filters+=("minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=$TARGET_FPS'")
        else
            video_filters+=("minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=30'")
        fi
    fi
    
    if [[ -n "$SCALE" ]]; then
        video_filters+=("scale=$SCALE:flags=lanczos")
    fi
    
    if [[ ${#video_filters[@]} -gt 0 ]]; then
        ffmpeg_cmd+=" -vf \"$(IFS=:; echo "${video_filters[*]}")\""
    fi
    
    # Add codec settings
    if [[ "$QUALITY" == "prores" ]]; then
        ffmpeg_cmd+=" -c:v prores_ks -profile:v 3 -pix_fmt $PIX_FMT"
    else
        ffmpeg_cmd+=" -c:v libx264"
        if [[ -n "$CRF" ]]; then
            ffmpeg_cmd+=" -crf $CRF"
        fi
        if [[ -n "$PRESET" ]]; then
            ffmpeg_cmd+=" -preset $PRESET"
        fi
        ffmpeg_cmd+=" -pix_fmt $PIX_FMT"
    fi
    
    ffmpeg_cmd+=" \"$output_mp4\""
    
    # Execute ffmpeg command
    log_info "Running: $ffmpeg_cmd"
    if eval $ffmpeg_cmd; then
        log_success "Created $output_mp4"
        PROCESSED_MP4S+=("$output_mp4")
    else
        log_error "Failed to create $output_mp4"
    fi
done

if [[ ${#PROCESSED_MP4S[@]} -eq 0 ]]; then
    log_error "No MP4 files were created successfully"
    exit 1
fi

# Concatenate all MP4s if requested
if [[ "$CONCAT" == true && ${#PROCESSED_MP4S[@]} -gt 1 ]]; then
    log_info "Concatenating ${#PROCESSED_MP4S[@]} MP4 files..."
    
    # Create concat list
    concat_file="$OUTPUT_DIR/batches.txt"
    rm -f "$concat_file"
    
    for mp4_file in "${PROCESSED_MP4S[@]}"; do
        printf "file '%s'\n" "$mp4_file" >> "$concat_file"
    done
    
    # Try stream copy first (faster, no re-encoding) - but only if no speed change
    concat_output="$OUTPUT_DIR/all_batches.mp4"
    
    if [[ "$SPEED" == "1.0" ]]; then
        log_info "Attempting stream copy concatenation..."
        if ffmpeg -y -f concat -safe 0 -i "$concat_file" -c copy "$concat_output" 2>/dev/null; then
            log_success "Created concatenated video: $concat_output"
        else
            log_warning "Stream copy failed, re-encoding..."
            if ffmpeg -y -f concat -safe 0 -i "$concat_file" \
                -c:v libx264 -crf $CRF -preset $PRESET -pix_fmt $PIX_FMT \
                "$concat_output"; then
                log_success "Created concatenated video (re-encoded): $concat_output"
            else
                log_error "Failed to create concatenated video"
            fi
        fi
    else
        # Speed change requires re-encoding
        log_info "Creating speed-adjusted concatenated video (${SPEED}x speed)..."
        if ffmpeg -y -f concat -safe 0 -i "$concat_file" \
            -filter:v "setpts=PTS/$SPEED" \
            -c:v libx264 -crf $CRF -preset $PRESET -pix_fmt $PIX_FMT \
            "$concat_output"; then
            log_success "Created speed-adjusted concatenated video (${SPEED}x): $concat_output"
        else
            log_error "Failed to create speed-adjusted concatenated video"
        fi
    fi
    
    # Clean up concat file
    rm -f "$concat_file"
fi

# Cleanup intermediate files if requested
if [[ "$CLEANUP" == true ]]; then
    log_info "Cleaning up intermediate files..."
    for mp4_file in "${PROCESSED_MP4S[@]}"; do
        if [[ -f "$mp4_file" ]]; then
            rm -f "$mp4_file"
            log_info "Removed $mp4_file"
        fi
    done
fi

# Summary
log_success "Processing complete!"
log_info "Created ${#PROCESSED_MP4S[@]} individual MP4 files"
if [[ "$CONCAT" == true && ${#PROCESSED_MP4S[@]} -gt 1 ]]; then
    log_info "Created concatenated video: $concat_output"
fi

# Show file sizes
log_info "File sizes:"
for mp4_file in "${PROCESSED_MP4S[@]}"; do
    if [[ -f "$mp4_file" ]]; then
        size=$(du -h "$mp4_file" | cut -f1)
        log_info "  $(basename "$mp4_file"): $size"
    fi
done

if [[ -f "$concat_output" ]]; then
    size=$(du -h "$concat_output" | cut -f1)
    log_info "  $(basename "$concat_output"): $size"
fi
