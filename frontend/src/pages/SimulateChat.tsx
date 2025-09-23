import React, { useMemo, useState } from 'react';
import {
  Box,
  Button,
  Container,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';

interface SimulateResponse {
  success: boolean;
  response?: string;
  conversation_stage?: string;
  qualification_data?: Record<string, any>;
  error?: string;
}

async function simulateChat(req: {
  from_number: string;
  text: string;
  first_name?: string;
  last_name?: string;
  property_address?: string;
  property_type?: string;
  campaign_id?: string;
}): Promise<SimulateResponse> {
  const res = await fetch('/simulate/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  return res.json();
}

type ChatMsg = { role: 'user' | 'agent'; text: string };

const SimulateChat: React.FC = () => {
  const [fromNumber, setFromNumber] = useState('+16095551234');
  const [firstName, setFirstName] = useState('Test');
  const [lastName, setLastName] = useState('Lead');
  const [propertyAddress, setPropertyAddress] = useState('123 Main St, Dallas, TX');
  const [propertyType, setPropertyType] = useState<'fix_flip' | 'vacant_land' | 'long_term_rental'>('fix_flip');
  const [campaignId, setCampaignId] = useState('incoming_response');

  const [input, setInput] = useState('Hello');
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [stage, setStage] = useState<string>('');
  const [qualData, setQualData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSend = useMemo(() => !!fromNumber && !!input && !loading, [fromNumber, input, loading]);

  const handleSend = async () => {
    if (!canSend) return;
    setError(null);
    setLoading(true);

    setMessages((prev) => [...prev, { role: 'user', text: input }]);

    try {
      const resp = await simulateChat({
        from_number: fromNumber,
        text: input,
        first_name: firstName,
        last_name: lastName,
        property_address: propertyAddress,
        property_type: propertyType,
        campaign_id: campaignId,
      });

      if (!resp.success) {
        setError(resp.error || 'Simulation failed');
      } else {
        if (resp.response) setMessages((prev) => [...prev, { role: 'agent', text: resp.response! }]);
        if (resp.conversation_stage) setStage(resp.conversation_stage);
        if (resp.qualification_data) setQualData(resp.qualification_data);
      }
    } catch (e: any) {
      setError(e?.message || 'Request failed');
    } finally {
      setLoading(false);
      setInput('');
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" fontWeight={700} gutterBottom>
        Simulation Chat (No SMS Cost)
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        This page uses the backend endpoint <code>/simulate/chat</code> to run the full agent flow without sending real SMS.
      </Typography>

      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          <TextField
            label="From Number"
            value={fromNumber}
            onChange={(e) => setFromNumber(e.target.value)}
            fullWidth
          />
          <TextField label="First Name" value={firstName} onChange={(e) => setFirstName(e.target.value)} fullWidth />
          <TextField label="Last Name" value={lastName} onChange={(e) => setLastName(e.target.value)} fullWidth />
        </Stack>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mt: 2 }}>
          <TextField
            label="Property Address"
            value={propertyAddress}
            onChange={(e) => setPropertyAddress(e.target.value)}
            fullWidth
          />
          <FormControl fullWidth>
            <InputLabel id="ptype-label">Property Type</InputLabel>
            <Select
              labelId="ptype-label"
              label="Property Type"
              value={propertyType}
              onChange={(e) => setPropertyType(e.target.value as any)}
            >
              <MenuItem value="fix_flip">Fix & Flip</MenuItem>
              <MenuItem value="vacant_land">Vacant Land</MenuItem>
              <MenuItem value="long_term_rental">Long-term Rental</MenuItem>
            </Select>
          </FormControl>
          <TextField label="Campaign ID" value={campaignId} onChange={(e) => setCampaignId(e.target.value)} fullWidth />
        </Stack>
      </Paper>

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
        <Paper variant="outlined" sx={{ p: 2, flex: 2, minHeight: 400 }}>
          <Typography variant="h6" gutterBottom>
            Chat
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Stack spacing={1} sx={{ minHeight: 300 }}>
            {messages.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                Start your test by typing a message below and pressing Send.
              </Typography>
            )}
            {messages.map((m, idx) => (
              <Box key={idx} sx={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                <Box
                  sx={{
                    px: 1.5,
                    py: 1,
                    borderRadius: 1,
                    bgcolor: m.role === 'user' ? 'primary.main' : 'grey.200',
                    color: m.role === 'user' ? 'white' : 'text.primary',
                    maxWidth: '80%',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {m.text}
                </Box>
              </Box>
            ))}
          </Stack>
          <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
            <TextField
              placeholder="Type a message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              fullWidth
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSend();
              }}
            />
            <Button variant="contained" onClick={handleSend} disabled={!canSend}>
              {loading ? 'Sending...' : 'Send'}
            </Button>
          </Stack>
          {error && (
            <Typography variant="body2" color="error" sx={{ mt: 1 }}>
              {error}
            </Typography>
          )}
        </Paper>

        <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
          <Typography variant="h6" gutterBottom>
            Conversation State
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="subtitle2">Stage</Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            {stage || '—'}
          </Typography>
          <Typography variant="subtitle2">Qualification Data</Typography>
          <Box component={Paper} variant="outlined" sx={{ p: 1, mt: 1, bgcolor: 'grey.50' }}>
            <pre style={{ margin: 0, fontSize: 12 }}>{JSON.stringify(qualData, null, 2)}</pre>
          </Box>
        </Paper>
      </Stack>
    </Container>
  );
};

export default SimulateChat;
