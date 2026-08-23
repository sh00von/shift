# Field Mapping

After you upload shorelines, SHIFT needs to know **which attribute holds the survey date**
and **how to read it**, plus how to handle positional **uncertainty**. This is the Field
Mapping dialog. Reopen it any time via **Add data → Configure Date & Fields…** or from the
Shorelines layer in the Layers panel.

## File preview

The top of the dialog shows the uploaded filename, feature count, and the list of columns
detected in the file.

## Date column

- **Column** — pick the property containing the date (auto-detected where possible).
- **Date format** — choose how to parse it:
  - **Auto-detect** — a robust parser that handles numeric years, ISO dates, US/EU orders,
    and extracts a year from messy strings.
  - **Common formats** — `DD/MM/YYYY`, `YYYY-MM-DD`, `MM/DD/YYYY`, `DD-MM-YYYY`, or year-only.
  - **Custom** — a `strftime` pattern such as `%d/%m/%Y`.

A **live preview table** shows the first ~20 rows with the raw value, the parsed date, and
the parsed year, so you can confirm the format is right before saving. Rows that fail to
parse are flagged.

## Uncertainty

Positional uncertainty (in metres) is used by Weighted Linear Regression and the forecast
cone. Options:

- **Use existing column** — select a numeric column already in your data.
- **Create a constant column** — give it a name; every survey gets the default value.
- **Use default value** — apply the **Default uncertainty (m)** (10 m by default) without
  adding a column.

## Saving

Click **Save**. SHIFT persists the mapping to the session and refreshes the shorelines layer.
You can now [cast transects](/docs/guide/cast-transects).
