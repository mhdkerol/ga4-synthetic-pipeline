{% macro normalize_currency_to_usd(currency_column) %}
  case when {{ currency_column }} is not null then 'USD' end
{% endmacro %}