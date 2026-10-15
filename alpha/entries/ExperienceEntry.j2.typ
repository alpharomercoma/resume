{% set lines = entry.main_column.splitlines()|reject("equalto", "")|list %}
[#entry(
  [{{ lines[0] }}],
  [{{ entry.date_and_location_column|replace("\n", " ") }}],
  [
{% for line in lines[1:] %}
    {{ line }}
{% endfor %}
  ],
)],
