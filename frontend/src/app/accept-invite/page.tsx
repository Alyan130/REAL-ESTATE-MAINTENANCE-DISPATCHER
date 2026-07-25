"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { AuthLayout } from "@/components/layout/auth-layout";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { acceptInvite } from "@/lib/api/auth";
import { toApiError } from "@/lib/errors";
import { homePathForRole, useAuthStore } from "@/stores/auth-store";

const MIN_PASSWORD_LENGTH = 8;

interface InviteFailure {
  message: string;
  tone: "danger" | "warn";
  /** Dead link that already produced an account — send them to sign in. */
  offerLogin?: boolean;
}

/**
 * Every invite failure has a different remedy, so none of them collapse into a
 * generic error. Mapped from backend/app/services/auth_service.py :: accept_invite.
 */
function describeFailure(error: unknown): InviteFailure {
  const { status, code, message, isNetworkError } = toApiError(error);

  if (isNetworkError) return { message, tone: "danger" };

  switch (code) {
    case "INVITE_SUPERSEDED":
      return {
        message:
          "A newer invite was sent, which made this link inactive. Open the most recent invite email instead.",
        tone: "warn",
      };
    case "INVITE_EXPIRED":
      return {
        message:
          "This invite link has expired. Ask your property manager to send a fresh invite.",
        tone: "warn",
      };
    case "INVITE_ALREADY_ACCEPTED":
      return {
        message: "This invite was already used. Your account is ready to sign in to.",
        tone: "warn",
        offerLogin: true,
      };
    case "PASSWORD_MISMATCH":
      return { message: "The two passwords don't match.", tone: "danger" };
    case "INVALID_TOKEN":
      return {
        message:
          "This invite link isn't valid. Check that you opened the full link from the email, or ask your property manager to resend it.",
        tone: "danger",
      };
    case "NOT_FOUND":
      return {
        message:
          "We couldn't find the account this invite belongs to. Ask your property manager to invite you again.",
        tone: "danger",
      };
  }

  // Fallback for a response that carried no code.
  if (status === 410) {
    return {
      message:
        "This invite link has expired. Ask your property manager to send a fresh invite.",
      tone: "warn",
    };
  }

  return { message, tone: "danger" };
}

function AcceptInviteForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const signIn = useAuthStore((state) => state.signIn);

  // The token rides in the query string; the user never types or sees it.
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [failure, setFailure] = useState<InviteFailure | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!token) {
    return (
      <div className="flex flex-col gap-4">
        <Alert tone="danger" title="No invite token in this link">
          Open the invite straight from your email — the link carries a token that
          this page needs. If you typed the address by hand, that token is missing.
        </Alert>
        <Link href="/login" className="text-sm font-semibold text-brand underline">
          Already have an account? Sign in
        </Link>
      </div>
    );
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFailure(null);
    setFieldError(null);

    if (password.length < MIN_PASSWORD_LENGTH) {
      setFieldError(`Use at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }

    if (password !== confirmPassword) {
      setFieldError("The two passwords don't match.");
      return;
    }

    setSubmitting(true);
    try {
      const { access_token } = await acceptInvite({
        token,
        password,
        confirm_password: confirmPassword,
      });

      // Accepting logs the user straight in — no bounce back to the login screen.
      const role = signIn(access_token);
      router.replace(role ? homePathForRole(role) : "/login");
    } catch (error) {
      setFailure(describeFailure(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      {failure ? (
        <Alert tone={failure.tone}>
          {failure.message}
          {failure.offerLogin ? (
            <>
              {" "}
              <Link href="/login" className="font-semibold text-brand underline">
                Go to sign in
              </Link>
            </>
          ) : null}
        </Alert>
      ) : null}

      <Input
        label="Create a password"
        type="password"
        autoComplete="new-password"
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        hint={`At least ${MIN_PASSWORD_LENGTH} characters.`}
      />

      <Input
        label="Confirm password"
        type="password"
        autoComplete="new-password"
        required
        value={confirmPassword}
        onChange={(event) => setConfirmPassword(event.target.value)}
        error={fieldError}
      />

      <Button type="submit" loading={submitting} fullWidth className="mt-2">
        Set password and continue
      </Button>
    </form>
  );
}

export default function AcceptInvitePage() {
  return (
    <AuthLayout
      title="Set up your account"
      subtitle="Choose a password and you'll be signed in straight away."
    >
      <Suspense fallback={null}>
        <AcceptInviteForm />
      </Suspense>
    </AuthLayout>
  );
}
