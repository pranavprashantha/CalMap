import { useQuery } from '@tanstack/react-query';
import { Button, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { API_BASE_URL, apiFetch } from '@/api/client';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';

type HealthResponse = {
  status: string;
  database: string;
};

/**
 * M0 walking skeleton: proves this device can reach the API on the dev machine and that
 * the API can reach Postgres. Replaced by the diary screen at M2.
 */
export default function HomeScreen() {
  const { data, error, isPending, isFetching, refetch } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiFetch<HealthResponse>('/health'),
    retry: false,
  });

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ThemedText type="title" style={styles.title}>
          CalMap
        </ThemedText>

        <ThemedView type="backgroundElement" style={styles.card}>
          <ThemedText type="small">API target</ThemedText>
          <ThemedText type="code">{API_BASE_URL}</ThemedText>

          <ThemedText type="small" style={styles.spaced}>
            Status
          </ThemedText>
          {isPending ? (
            <ThemedText type="code">checking…</ThemedText>
          ) : error ? (
            // Surfaced in full on purpose: at M0 this message is the debugging tool for
            // firewall rules and wrong-adapter IPs.
            <ThemedText type="code">unreachable — {error.message}</ThemedText>
          ) : (
            <ThemedText type="code">
              api {data.status} · database {data.database}
            </ThemedText>
          )}
        </ThemedView>

        <Button
          title={isFetching ? 'Checking…' : 'Retry'}
          onPress={() => refetch()}
          disabled={isFetching}
        />
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    flexDirection: 'row',
  },
  safeArea: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: Spacing.four,
    gap: Spacing.four,
    paddingBottom: BottomTabInset + Spacing.three,
    maxWidth: MaxContentWidth,
  },
  title: {
    textAlign: 'center',
  },
  card: {
    alignSelf: 'stretch',
    gap: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.four,
    borderRadius: Spacing.four,
  },
  spaced: {
    marginTop: Spacing.three,
  },
});
