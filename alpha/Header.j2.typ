#header(
  "{{ cv._plain_name|replace("\\", "\\\\")|replace("\"", "\\\"") }}",
  [{{ cv.headline }}],
  (
{% if cv.email %}
    link("mailto:{{ cv.email }}")[{{ cv.email|replace("@", "\\@") }}],
{% endif %}
{% if cv.website %}
    link("{{ cv.website }}")[{{ cv.website|clean_url }}],
{% endif %}
{% for network in cv.social_networks or [] %}
    link("{{ network.url }}")[{{ network.url|clean_url }}],
{% endfor %}
  ),
)

// Everything after the header marks its links with the external-link icon.
#show link: linked
