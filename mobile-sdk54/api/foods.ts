import { apiFetch } from '@/api/client';

export type FoodSearchResult = {
  id: number;
  food_name: string;
  brand_name: string | null;
  data_type: string | null;
  // Numeric columns arrive as strings: JSON has no decimal type, and sending them
  // as floats would quietly round macro values.
  calories_per_100g: string | null;
  protein_per_100g: string | null;
  carbs_per_100g: string | null;
  fat_per_100g: string | null;
  default_serving_g: string | null;
};

export function searchFoods(query: string): Promise<FoodSearchResult[]> {
  return apiFetch<FoodSearchResult[]>(`/foods/search?q=${encodeURIComponent(query)}`);
}
