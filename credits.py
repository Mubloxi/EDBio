"""Vista Genomics credit calculations."""

from species import SpeciesDB


def format_credits(value):
    """Format a credit value for display."""
    if value is None:
        return "Unknown"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M CR"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K CR"
    return f"{value} CR"


class CreditCalculator:
    def __init__(self):
        self.db = SpeciesDB()

    def species_value(self, species_name):
        return self.db.species_price(species_name)

    def collection_value(self, species_name, completed):
        """Value of a species collection if completed, else None."""
        if not completed:
            return None
        return self.db.species_price(species_name)

    def planet_value(self, species_values):
        """Sum of completed species values on a planet."""
        total = 0
        for value in species_values:
            if value:
                total += value
        return total

    def first_footfall_value(self, base_value):
        """Estimated first-footfall payout. Not guaranteed."""
        multiplier = self.db.first_footfall_multiplier()
        return base_value * multiplier
