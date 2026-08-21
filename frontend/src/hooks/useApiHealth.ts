import { useEffect, useState } from 'react';
import axios from 'axios';

import { apiGet } from '../services/api';

type ProfileProbeResponse = Record<string, unknown>;

export interface ApiHealthState {
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;

    if (status === 401) {
      return 'Unauthorized: connect with a valid Supabase session.';
    }

    if (typeof status === 'number') {
      return `HTTP ${status}: ${error.message}`;
    }

    if (error.message) {
      return error.message;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Unable to reach the API.';
}

export function useApiHealth(): ApiHealthState {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const checkConnection = async (): Promise<void> => {
      try {
        await apiGet<ProfileProbeResponse>('/users/profile');

        if (!isActive) {
          return;
        }

        setIsConnected(true);
        setError(null);
      } catch (caughtError: unknown) {
        if (!isActive) {
          return;
        }

        setIsConnected(false);
        setError(getErrorMessage(caughtError));
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    };

    void checkConnection();

    return () => {
      isActive = false;
    };
  }, []);

  return { isConnected, isLoading, error };
}
