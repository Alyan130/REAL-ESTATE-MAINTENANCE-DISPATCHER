"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { AuthLayout } from "@/components/layout/auth-layout";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { login } from "@/lib/api/auth";
import { toApiError } from "@/lib/errors";
import { homePathForRole, useAuthStore } from "@/stores/auth-store";

interface LoginFailure {
  message: string;
  /** Pending invites are a state the user can act on, not a hard failure. */
  tone: "danger" | "warn";
}

/**
 * The backend returns three distinguishable outcomes, and the user needs a
 * different next step for each:
 *   INVALID_CREDENTIALS -> deliberately doesn't say which of the two was wrong
 *   ACCOUNT_DISABLED    -> only the PM can undo this
 *   ACCOUNT_PENDING     -> the invite was never accepted
 * Status codes are kept as a fallback for anything that answers without a code.
 */
function describeFailure(error: unknown): LoginFailure {
  const { status, code, message, isNetworkError } = toApiError(error);

  if (isNetworkError) {
    return { message, tone: "danger" };
  }

  if (code === "ACCOUNT_PENDING" || status === 403) {
    return {
      message:
        "This account hasn't been set up yet. Check your email for the invite link and set a password first.",
      tone: "warn",
    };
  }

  if (code === "ACCOUNT_DISABLED") {
    return {
      message:
        "This account has been disabled. Contact your property manager to get access back.",
      tone: "danger",
    };
  }

  if (code === "INVALID_CREDENTIALS" || status === 401) {
    return { message: "That email and password don't match.", tone: "danger" };
  }

  return { message, tone: "danger" };
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const signIn = useAuthStore((state) => state.signIn);
  const hydrated = useAuthStore((state) => state.hydrated);
  const role = useAuthStore((state) => state.role);
  const token = useAuthStore((state) => state.token);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [failure, setFailure] = useState<LoginFailure | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const sessionExpired = searchParams.get("reason") === "expired";

  // Someone already signed in has no business on this screen.
  useEffect(() => {
    if (hydrated && token && role) {
      router.replace(homePathForRole(role));
    }
  }, [hydrated, token, role, router]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFailure(null);
    setSubmitting(true);

    try {
      const { access_token } = await login({ email: email.trim(), password });
      const signedInRole = signIn(access_token, email.trim());

      if (!signedInRole) {
        setFailure({
          message: "We couldn't read your account details. Please try again.",
          tone: "danger",
        });
        return;
      }

      router.replace(homePathForRole(signedInRole));
    } catch (error) {
      // The password is intentionally left in place so the user can correct the
      // email without retyping it.
      setFailure(describeFailure(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      {sessionExpired && !failure ? (
        <Alert tone="info">Your session ended. Please sign in again.</Alert>
      ) : null}

      {failure ? <Alert tone={failure.tone}>{failure.message}</Alert> : null}

      <Input
        label="Email"
        type="email"
        autoComplete="email"
        required
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        placeholder="you@example.com"
      />

      <Input
        label="Password"
        type="password"
        autoComplete="current-password"
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />

      <Button type="submit" loading={submitting} fullWidth className="mt-2">
        Sign in
      </Button>

      <p className="text-center text-sm text-muted">
        Accounts are created by invitation from a property manager.
      </p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <AuthLayout
      title="Sign in"
      subtitle="Property managers, tenants, and vendors all start here."
    >
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </AuthLayout>
  );
}
