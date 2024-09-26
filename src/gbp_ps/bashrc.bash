if [[ -f /Makefile.gbp && "${EBUILD_PHASE}" != depend ]]; then
    BUILD_HOST="$(uname -n)"
    WGET_BODY=\{\"query\":\ \"mutation\ \{addBuildProcess\(process:\{machine:\\\"${BUILD_MACHINE}\\\",buildHost:\\\"${BUILD_HOST}\\\",package:\\\"${CATEGORY}/${PF}\\\",id:\\\"${BUILD_NUMBER}\\\",phase:\\\"${EBUILD_PHASE}\\\",startTime:\\\""$(date -u +%Y-%m-%dT%H:%M:%S.%N+00:00)"\\\"\}\)\{message\}\}\",\ \"variables\":\ null\}
    wget \
        --body-data="${WGET_BODY}" \
        --header="Content-type: application/json" \
        --method=POST \
        --no-check-certificate \
        --output-document=/dev/null \
        --quiet \
        http://gbp/graphql
fi
