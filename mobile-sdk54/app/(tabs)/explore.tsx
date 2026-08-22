import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  TextInput,
  useColorScheme,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { searchFoods, type FoodSearchResult } from '@/api/foods';
import { useDebouncedValue } from '@/hooks/use-debounced-value';

function round(value: string | null): string {
  if (value === null) return '—';
  return String(Math.round(Number(value)));
}

export default function SearchScreen() {
  const isDark = useColorScheme() === 'dark';
  const [text, setText] = useState('');
  const debounced = useDebouncedValue(text);

  const { data, error, isFetching } = useQuery({
    queryKey: ['foods', 'search', debounced],
    queryFn: () => searchFoods(debounced),
    // A blank box should show nothing, not every food in the database.
    enabled: debounced.trim().length > 0,
    retry: false,
  });

  const palette = {
    text: isDark ? '#ECEDEE' : '#11181C',
    muted: isDark ? '#9BA1A6' : '#687076',
    card: isDark ? '#1C1F21' : '#F1F3F5',
    border: isDark ? '#2A2E31' : '#E1E4E8',
  };

  const renderItem = ({ item }: { item: FoodSearchResult }) => (
    <View style={[styles.row, { borderBottomColor: palette.border }]}>
      <Text style={[styles.name, { color: palette.text }]} numberOfLines={2}>
        {item.food_name}
      </Text>
      <Text style={[styles.macros, { color: palette.muted }]}>
        {round(item.calories_per_100g)} kcal · P {round(item.protein_per_100g)}g · C{' '}
        {round(item.carbs_per_100g)}g · F {round(item.fat_per_100g)}g
        <Text style={styles.per100}> per 100g</Text>
      </Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: palette.text }]}>Search foods</Text>
        <TextInput
          value={text}
          onChangeText={setText}
          placeholder="chicken breast"
          placeholderTextColor={palette.muted}
          autoCorrect={false}
          autoCapitalize="none"
          returnKeyType="search"
          style={[styles.input, { backgroundColor: palette.card, color: palette.text }]}
        />
      </View>

      {error ? (
        <Text style={[styles.status, { color: palette.muted }]}>
          Search failed — {error.message}
        </Text>
      ) : debounced.trim().length === 0 ? (
        <Text style={[styles.status, { color: palette.muted }]}>
          Type to search 8,000+ USDA foods.
        </Text>
      ) : isFetching && !data ? (
        <ActivityIndicator style={styles.spinner} />
      ) : data && data.length === 0 ? (
        <Text style={[styles.status, { color: palette.muted }]}>
          No foods matched “{debounced}”.
        </Text>
      ) : (
        <FlatList
          data={data}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={styles.list}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 12,
    gap: 12,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
  },
  input: {
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
  },
  status: {
    paddingHorizontal: 20,
    paddingTop: 24,
    fontSize: 14,
  },
  spinner: {
    paddingTop: 32,
  },
  list: {
    paddingHorizontal: 20,
    paddingTop: 12,
  },
  row: {
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    gap: 4,
  },
  name: {
    fontSize: 15,
    fontWeight: '500',
  },
  macros: {
    fontSize: 13,
  },
  per100: {
    fontStyle: 'italic',
  },
});
