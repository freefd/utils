#!/usr/bin/env bash

# Reads EXIF creation date from all media files in
# current directory and moves them carefully under
#
#   BASEDIR/YYYY/MM/DD/YYYY-MM-DD_HHMMSS_XXHASH.EXTENSION
#
# where 'carefully' means that it does not overwrite
# differing files if they already exist and will not delete
# the original file if copying fails for some reason.

# This script was originally written and put into
# Public Domain by Jarno Elonen <elonen@iki.fi> in June 2003.
# Feel free to do whatever you like with it.

# Improve error handling
set -o errexit
set -o pipefail

# Activate debugging from here
#set -o xtrace
#set -o verbose

# Enable handling of filenames with spaces:
_saveIFS=$IFS
IFS=$(echo -en "\n\b")

# Useful functions
__info() { __log 'INFO' $1; }
__debug() { __log 'DEBUG' $1; }
__warn() { __log 'WARN' $1; }
__notice() { __log 'NOTICE' $1; }
__error() { __log 'ERROR' $1; }
__log() {
     local level=${1?}
     shift
     local line="[$(date '+%F %T')] $level: $*"
     echo "$line"
}

__usage() {
cat << EOF
usage: $0 options

OPTIONS:
   -h      Show this message
   -n      Run in Dry run Mode. Default: False
   -b      Based directory for output sorted files. Default: ${_defaultBaseDirectory}
   -d      Run in Debug Mode. Default: False
EOF
}

# Defaults
_requiredTools=(exiftool jq date xxh32sum rsync) # Also change settings below if changing this, the output should be in the format YYYY:MM:DD
_defaultBaseDirectory='/path/to/media/sorted'

# Check whether needed programs are installed
for requiredTool in ${_requiredTools[*]}
do
    command -v $requiredTool 2>&1 >/dev/null || { __error "[CRT] $requiredTool is required but not installed. Aborting."; exit 1; }
done

while getopts “hnb:d” OPTION
do
    case $OPTION in
        h)
            __usage
            exit 1
            ;;
        b)
            _baseDirectory=${OPTARG}
            ;;
        n)
            _dryRunMode=true
            ;;
        d)
            _debugMode=true
            ;;
        ?)
            __usage
            exit
            ;;
    esac
done

if [[ -z "${_baseDirectory}" ]]; then
    _baseDirectory=${_defaultBaseDirectory}
fi

[ ${_dryRunMode} ] && __info "Running in Dry run mode" || __info "Running in Production mode"

for inputFilePath in $(find $(pwd -P) -not -wholename "*._*" -iname "*.JPG" -or -iname "*.JPEG" -or -iname "*.CRW" -or -iname "*.THM" -or -iname "*.RW2" -or -iname "*.ARW" -or -iname "*.AVI" -or -iname "*.MOV" -or -iname "*.MP4" -or -iname "*.MPG" -or -iname "*.3GP" -or -iname "*.MTS" -or -iname "*.PNG")
do
    inputFileExtension=${inputFilePath##*.}

    [ ${_debugMode} ] && __debug "Input file path: ${inputFilePath}"

    if [[ "$inputFileExtension" =~ ^(MP4|mp4|MPG|mpg|MOV|mov)$ ]]
    then
        # Special date handling for video files due to storing date time in UTC
        # Do not use for 3GP format
        inputFileDate=$(exiftool -quiet -tab -dateformat "%Y:%m:%d:%H:%M:%S" -json -DateTimeOriginal -api QuickTimeUTC "${inputFilePath}" | jq --raw-output '.[].DateTimeOriginal.val')
    else
        inputFileDate=$(exiftool -quiet -tab -dateformat "%Y:%m:%d:%H:%M:%S" -json -DateTimeOriginal "${inputFilePath}" | jq --raw-output '.[].DateTimeOriginal.val')
    fi

    [ ${_debugMode} ] && __debug "EXIF original file date: $inputFileDate"

    if [ "$inputFileDate" == "null" ]  # If exif extraction with inputFileDateTimeOriginal failed
    then
        if [[ "$inputFileExtension" =~ ^(MP4|mp4|MPG|mpg|MOV|mov)$ ]]
        then
            # Special date handling for video files due to storing date time in UTC
            # Do not use for 3GP format
            inputFileDate=$(exiftool -quiet -tab -dateformat "%Y:%m:%d:%H:%M:%S" -json -MediaCreateDate -api QuickTimeUTC "${inputFilePath}" | jq --raw-output '.[].MediaCreateDate.val')
        else
            inputFileDate=$(exiftool -quiet -tab -dateformat "%Y:%m:%d:%H:%M:%S" -json -MediaCreateDate "${inputFilePath}" | jq --raw-output '.[].MediaCreateDate.val')
        fi
    fi

    [ ${_debugMode} ] && __debug "EXIF create file date: $inputFileDate"

    if [ -z "$inputFileDate" ] || [ "$inputFileDate" == "null" ] || [ "$inputFileDate" == "0000:00:00 00:00:00" ] || [[ "$inputFileDate" =~ ^1904:01:01 ]]
    then
        # If exif extraction failed
        inputFileDate=$(date +%Y:%m:%d:%H:%M:%S -r "${inputFilePath}")
    fi

    [ ${_debugMode} ] && __debug "File create date: $inputFileDate"

    if [ ! -z "$inputFileDate" ]; # Doublecheck
    then
        inputFileYear=$(echo $inputFileDate | cut -d: -f1)
        inputFileMonth=$(echo $inputFileDate | cut -d: -f2)
        inputFileDay=$(echo $inputFileDate | cut -d: -f3)
        inputFileHour=$(echo $inputFileDate | cut -d: -f4)
        inputFileMinute=$(echo $inputFileDate | cut -d: -f5)
        inputFileSecond=$(echo $inputFileDate | cut -d: -f6)

        if [ ${inputFileYear#0} -gt 0 ] & [ ${inputFileMonth#0} -gt 0 ] & [ ${inputFileDay#0} -gt 0 ]
        then
            inputFileXxhash=$(xxh32sum ${inputFilePath} | awk '{print $1}')
            outputDirectory=${_baseDirectory}/${inputFileYear}/${inputFileMonth}/${inputFileDay}
            outputFilePath=${outputDirectory}/${inputFileYear}-${inputFileMonth}-${inputFileDay}_${inputFileHour:-00}${inputFileMinute}${inputFileSecond}_${inputFileXxhash}.${inputFileExtension}

            [ ${_debugMode} ] && __debug "Output file path: ${outputFilePath}"
            [ ! ${_dryRunMode} ] && mkdir -pv "${outputDirectory}"

            if [ -e "$outputFilePath" ] && ! cmp -s "$inputFilePath" "$outputFilePath"
            then
                __warn "'$outputFilePath' exists already and is different from '$inputFilePath'"
            else
                if [ ! ${_dryRunMode} ]
                then    
                    __info "Copying '$inputFilePath' to '$outputFilePath'"
                    rsync -ah --progress "$inputFilePath" "$outputFilePath"
                    if ! cmp -s "$inputFilePath" "$outputFilePath"
                    then
                        __warn "Copying failed somehow, will not delete original '$inputFilePath'"
                    else
                        [ ${_debugMode} ] && __debug "Removing source '$inputFilePath'"
                        rm -f $inputFilePath
                    fi
                else
                    __notice "Intent to move '$inputFilePath' to '$outputFilePath'"
                fi
            fi
        else
           __warn "'$inputFilePath' doesn't contain create date"
        fi
    else
        __warn "'$inputFilePath' doesn't contain create date"
    fi
done

# restore $IFS
IFS=$_saveIFS
