if [[ "${EBUILD_PHASE}" != depend ]]; then
    gbp add-process -l /var/tmp/portage/gbpps.db localhost 0 "${CATEGORY}/${PF}" "${EBUILD_PHASE}"
fi
