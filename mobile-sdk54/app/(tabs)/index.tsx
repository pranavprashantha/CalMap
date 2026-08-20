import { useQuery } from '@tanstack/react-query';
import { Button, StyleSheet, Text, useColorScheme, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { API_BASE_URL, apiFetch } from '@/api/client';

type HealthResponse = {
  status: string;
  database: string;
};

/**
 * M0 walking skeleton: proves this device can reach the API on the dev machine and that
 * the API can reach Postgres. Replaced by the diary screen at M2.
 */
export default function HomeScreen() {
  const isDark = useColorScheme() === 'dark';
  const { data, error, isPending, isFetching, refetch } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiFetch<HealthResponse>('/health'),
    retry: false,
  });

  const textColor = { color: isDark ? '#ECEDEE' : '#11181C' };
  const cardStyle = { backgroundColor: isDark ? '#1C1F21' : '#F1F3F5' };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.content}>
        <Text style={[styles.title, textColor]}>CalMap</Text>

        <View style={[styles.card, cardStyle]}>
          <Text style={[styles.label, textColor]}>API target</Text>
          <Text style={[styles.mono, textColor]}>{API_BASE_URL}</Text>

          <Text style={[styles.label, styles.spaced, textColor]}>Status</Text>
          {isPending ? (
            <Text style={[styles.mono, textColor]}>checking…</Text>
          ) : error ? (
            // Surfaced in full on purpose: at M0 this message is the debugging tool for
            // firewall rules and wrong-adapter IPs.
            <Text style={[styles.mono, textColor]}>unreachable — {error.message}</Text>
          ) : (
            <Text style={[styles.mono, textColor]}>
              api {data.status} · database {data.database}
            </Text>
          )}
        </View>

        <Button
          title={isFetching ? 'Checking…' : 'Retry'}
          onPress={() => refetch()}
          disabled={isFetching}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
    gap: 24,
  },
  title: {
    fontSize: 32,
    fontWeight: '700',
    textAlign: 'center',
  },
  card: {
    gap: 6,
    padding: 20,
    borderRadius: 16,
  },
  label: {
    fontSize: 12,
    opacity: 0.6,
    textTransform: 'uppercase',
  },
  mono: {
    fontFamily: 'monospace',
    fontSize: 14,
  },
  spaced: {
    marginTop: 16,
  },
});
