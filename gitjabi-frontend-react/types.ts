import React from 'react';

export type ViewType = 'dashboard' | 'review-stage' | 'compliance' | 'context-hub' | 'audit';

export interface RepoMetric {
  id: string;
  name: string;
  branch: string;
  language: string;
  healthScore: number;
  openIssues: number;
  lastAudit: string;
}

export interface PRItem {
  id: string;
  prId: string;
  title: string;
  timeAgo: string;
  status: 'Pending Review' | 'Approved' | 'Policy Flagged' | 'Analysis Running';
  statusColor: 'yellow' | 'green' | 'red' | 'blue';
}

export interface KPIProps {
  title: string;
  value: string;
  change: string;
  changeType: 'positive' | 'negative';
  changeText: string;
  icon?: React.ReactNode;
  chart?: React.ReactNode;
}