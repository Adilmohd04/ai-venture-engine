import { useState, useEffect } from "react";
import { Users, UserPlus, Crown, Mail, Trash2, Check, X } from "lucide-react";
import { authFetch } from "../lib/supabase";
import { useAuth } from "../contexts/AuthContext";

export default function TeamPanel() {
  const { profile, refreshProfile } = useAuth();
  const [team, setTeam] = useState(null);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [teamName, setTeamName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [creating, setCreating] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadTeamData();
  }, [profile]);

  async function loadTeamData() {
    setLoading(true);
    try {
      // Load team info
      const teamRes = await authFetch("/api/teams/mine");
      if (teamRes.ok) {
        const data = await teamRes.json();
        setTeam(data);
      } else {
        setTeam(null);
      }

      // Load pending invitations for current user
      const invRes = await authFetch("/api/invitations");
      if (invRes.ok) {
        setInvitations(await invRes.json());
      }
    } catch {
      /* ignore */
    }
    setLoading(false);
  }

  async function handleCreateTeam(e) {
    e.preventDefault();
    if (!teamName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const res = await authFetch("/api/teams", {
        method: "POST",
        body: JSON.stringify({ name: teamName.trim() }),
      });
      if (res.ok) {
        setTeamName("");
        if (refreshProfile) await refreshProfile();
        await loadTeamData();
      } else {
        const data = await res.json();
        setError(data.detail || "Failed to create team");
      }
    } catch {
      setError("Failed to create team");
    }
    setCreating(false);
  }

  async function handleInvite(e) {
    e.preventDefault();
    if (!inviteEmail.trim() || !team) return;
    setInviting(true);
    setError(null);
    try {
      const res = await authFetch(`/api/teams/${team.id}/invite`, {
        method: "POST",
        body: JSON.stringify({ email: inviteEmail.trim() }),
      });
      if (res.ok) {
        setInviteEmail("");
        await loadTeamData();
      } else {
        const data = await res.json();
        setError(data.detail || "Failed to send invitation");
      }
    } catch {
      setError("Failed to send invitation");
    }
    setInviting(false);
  }

  async function handleRevokeInvitation(invId) {
    if (!team) return;
    try {
      const res = await authFetch(`/api/teams/${team.id}/invitations/${invId}`, {
        method: "DELETE",
      });
      if (res.ok) await loadTeamData();
    } catch {
      /* ignore */
    }
  }

  async function handleRemoveMember(userId) {
    if (!team) return;
    try {
      const res = await authFetch(`/api/teams/${team.id}/members/${userId}`, {
        method: "DELETE",
      });
      if (res.ok) await loadTeamData();
    } catch {
      /* ignore */
    }
  }

  async function handleAcceptInvitation(invId) {
    try {
      const res = await authFetch(`/api/invitations/${invId}/accept`, {
        method: "POST",
      });
      if (res.ok) {
        if (refreshProfile) await refreshProfile();
        await loadTeamData();
      } else {
        const data = await res.json();
        setError(data.detail || "Failed to accept invitation");
      }
    } catch {
      setError("Failed to accept invitation");
    }
  }

  async function handleDeclineInvitation(invId) {
    try {
      const res = await authFetch(`/api/invitations/${invId}/decline`, {
        method: "POST",
      });
      if (res.ok) await loadTeamData();
    } catch {
      /* ignore */
    }
  }

  // Non-business users see nothing
  if (!profile || (profile.plan !== "business" && !team && invitations.length === 0)) {
    return null;
  }

  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-6 mb-8">
        <div className="flex items-center gap-3 text-slate-500">
          <div className="w-5 h-5 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
          <span className="text-sm">Loading team info...</span>
        </div>
      </div>
    );
  }

  const isOwner = team?.owner_id === profile?.id;
  const pendingInvitations = team?.invitations?.filter((i) => i.status === "pending") || [];
  const creditUsed = team?.team_credits_used ?? 0;
  const creditLimit = team?.team_credits_limit ?? 0;
  const creditPercent = creditLimit > 0 ? Math.min((creditUsed / creditLimit) * 100, 100) : 0;

  return (
    <div className="mb-8 space-y-4">
      {/* Error banner */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 flex items-center gap-3">
          <span className="text-rose-600 text-sm flex-1">{error}</span>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-600">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Pending invitations for current user (received) */}
      {invitations.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Mail size={18} className="text-indigo-500" />
            <h3 className="text-sm font-semibold text-slate-900">Team Invitations</h3>
          </div>
          <div className="space-y-3">
            {invitations.map((inv) => (
              <div
                key={inv.id}
                className="flex items-center justify-between bg-slate-50 rounded-xl px-4 py-3"
              >
                <div>
                  <p className="text-sm font-medium text-slate-900">{inv.team_name}</p>
                  <p className="text-xs text-slate-500">Invited to join</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleAcceptInvitation(inv.id)}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1"
                  >
                    <Check size={14} />
                    Accept
                  </button>
                  <button
                    onClick={() => handleDeclineInvitation(inv.id)}
                    className="px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 rounded-lg text-xs font-medium transition-colors flex items-center gap-1"
                  >
                    <X size={14} />
                    Decline
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* User is on a team */}
      {team && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          {/* Team header */}
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center">
                <Users size={20} className="text-indigo-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-900">{team.name}</h3>
                <p className="text-xs text-slate-500">
                  {team.members?.length || 0} member{(team.members?.length || 0) !== 1 ? "s" : ""}
                </p>
              </div>
            </div>
            {isOwner && (
              <span className="px-2.5 py-1 bg-amber-50 border border-amber-200 text-amber-700 rounded-full text-xs font-semibold flex items-center gap-1">
                <Crown size={12} />
                Owner
              </span>
            )}
          </div>

          {/* Credit usage bar */}
          <div className="mb-5">
            <div className="flex items-center justify-between text-xs text-slate-600 mb-1.5">
              <span>Team Credits</span>
              <span className="font-medium">{creditUsed} / {creditLimit}</span>
            </div>
            <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  creditPercent >= 90 ? "bg-rose-500" : creditPercent >= 70 ? "bg-amber-500" : "bg-indigo-500"
                }`}
                style={{ width: `${creditPercent}%` }}
              />
            </div>
          </div>

          {/* Member list */}
          <div className="mb-5">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Members</h4>
            <div className="space-y-2">
              {(team.members || []).map((member) => (
                <div
                  key={member.user_id}
                  className="flex items-center justify-between bg-slate-50 rounded-xl px-4 py-2.5"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-semibold text-xs">
                      {(member.full_name || member.email || "?").charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-900">
                        {member.full_name || member.email}
                      </p>
                      {member.full_name && (
                        <p className="text-xs text-slate-500">{member.email}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {member.role === "owner" ? (
                      <span className="px-2 py-0.5 bg-amber-50 border border-amber-200 text-amber-700 rounded-full text-[10px] font-semibold flex items-center gap-1">
                        <Crown size={10} />
                        Owner
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 bg-slate-100 border border-slate-200 text-slate-600 rounded-full text-[10px] font-semibold">
                        Member
                      </span>
                    )}
                    {isOwner && member.role !== "owner" && (
                      <button
                        onClick={() => handleRemoveMember(member.user_id)}
                        className="p-1 text-slate-400 hover:text-rose-500 transition-colors"
                        title="Remove member"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Owner: Invite form + pending invitations */}
          {isOwner && (
            <>
              <div className="border-t border-slate-100 pt-4 mb-4">
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                  Invite Member
                </h4>
                <form onSubmit={handleInvite} className="flex gap-2">
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="colleague@company.com"
                    className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300"
                    required
                  />
                  <button
                    type="submit"
                    disabled={inviting}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-400 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5"
                  >
                    <UserPlus size={14} />
                    {inviting ? "Sending..." : "Invite"}
                  </button>
                </form>
              </div>

              {pendingInvitations.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                    Pending Invitations
                  </h4>
                  <div className="space-y-2">
                    {pendingInvitations.map((inv) => (
                      <div
                        key={inv.id}
                        className="flex items-center justify-between bg-slate-50 rounded-xl px-4 py-2.5"
                      >
                        <div className="flex items-center gap-2">
                          <Mail size={14} className="text-slate-400" />
                          <span className="text-sm text-slate-700">{inv.email}</span>
                        </div>
                        <button
                          onClick={() => handleRevokeInvitation(inv.id)}
                          className="p-1 text-slate-400 hover:text-rose-500 transition-colors"
                          title="Revoke invitation"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Business user with no team — Create Team CTA */}
      {!team && profile?.plan === "business" && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center">
              <Users size={20} className="text-indigo-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Create a Team</h3>
              <p className="text-xs text-slate-500">
                Collaborate with colleagues on deal flow analysis
              </p>
            </div>
          </div>
          <form onSubmit={handleCreateTeam} className="flex gap-2">
            <input
              type="text"
              value={teamName}
              onChange={(e) => setTeamName(e.target.value)}
              placeholder="Team name"
              maxLength={100}
              className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300"
              required
            />
            <button
              type="submit"
              disabled={creating}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-400 text-white rounded-lg text-sm font-medium transition-colors"
            >
              {creating ? "Creating..." : "Create Team"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
