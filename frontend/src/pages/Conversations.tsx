import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  List,
  ListItem,
  ListItemText,
  Paper,
  TextField,
  Typography,
  Button,
  Avatar,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Send as SendIcon,
  Person as PersonIcon,
  SmartToy as BotIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { conversationApi, leadApi } from '../services/api';
import { Conversation, ConversationStatus, LeadStatus } from '../types';

const Conversations: React.FC = () => {
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [newMessage, setNewMessage] = useState('');
  const [filters, setFilters] = useState({
    status: '',
  });

  const queryClient = useQueryClient();

  const { data: conversationsData } = useQuery(
    ['conversations', filters],
    () => conversationApi.getAll(filters)
  );

  const { data: selectedConversationData } = useQuery(
    ['conversation', selectedConversation],
    () => conversationApi.getById(selectedConversation!),
    { enabled: !!selectedConversation }
  );

  const { data: leadsData } = useQuery('leads', () => leadApi.getAll());

  const sendMessageMutation = useMutation(
    ({ leadId, message }: { leadId: string; message: string }) =>
      conversationApi.sendMessage(leadId, message),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['conversation', selectedConversation]);
        queryClient.invalidateQueries('conversations');
        setNewMessage('');
      },
    }
  );

  const handleSendMessage = () => {
    if (newMessage.trim() && selectedConversationData) {
      sendMessageMutation.mutate({
        leadId: selectedConversationData.lead_id,
        message: newMessage.trim(),
      });
    }
  };

  const getStatusColor = (status: ConversationStatus) => {
    switch (status) {
      case ConversationStatus.ACTIVE:
        return 'success';
      case ConversationStatus.WAITING_RESPONSE:
        return 'warning';
      case ConversationStatus.QUALIFIED:
        return 'info';
      case ConversationStatus.APPOINTMENT_SET:
        return 'success';
      case ConversationStatus.CLOSED:
        return 'default';
      default:
        return 'default';
    }
  };

  const getLeadName = (leadId: string) => {
    const lead = leadsData?.leads?.find(l => l.id === leadId);
    return lead ? `${lead.first_name} ${lead.last_name}` : 'Unknown Lead';
  };

  const getLeadPhone = (leadId: string) => {
    const lead = leadsData?.leads?.find(l => l.id === leadId);
    return lead?.phone || '';
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Conversations
      </Typography>

      <Grid container spacing={3} sx={{ height: 'calc(100vh - 200px)' }}>
        {/* Conversations List */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
              <FormControl fullWidth size="small">
                <InputLabel>Filter by Status</InputLabel>
                <Select
                  value={filters.status}
                  label="Filter by Status"
                  onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                >
                  <MenuItem value="">All Conversations</MenuItem>
                  {Object.values(ConversationStatus).map((status) => (
                    <MenuItem key={status} value={status}>
                      {status.replace('_', ' ').toUpperCase()}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
            
            <List sx={{ flexGrow: 1, overflow: 'auto' }}>
              {conversationsData?.conversations?.map((conversation) => (
                <ListItem
                  key={conversation.id}
                  button
                  selected={selectedConversation === conversation.id}
                  onClick={() => setSelectedConversation(conversation.id)}
                  sx={{
                    borderBottom: 1,
                    borderColor: 'divider',
                    '&:hover': { backgroundColor: 'action.hover' },
                  }}
                >
                  <ListItemText
                    primary={
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="subtitle2">
                          {getLeadName(conversation.lead_id)}
                        </Typography>
                        <Chip
                          label={conversation.status}
                          color={getStatusColor(conversation.status)}
                          size="small"
                        />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" color="textSecondary">
                          {getLeadPhone(conversation.lead_id)}
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          {conversation.messages?.length || 0} messages • {formatTimestamp(conversation.updated_at)}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>

        {/* Conversation Detail */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {selectedConversationData ? (
              <>
                {/* Conversation Header */}
                <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
                  <Typography variant="h6">
                    {getLeadName(selectedConversationData.lead_id)}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    {getLeadPhone(selectedConversationData.lead_id)}
                  </Typography>
                  <Chip
                    label={selectedConversationData.status}
                    color={getStatusColor(selectedConversationData.status)}
                    size="small"
                    sx={{ mt: 1 }}
                  />
                </Box>

                {/* Messages */}
                <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
                  {selectedConversationData.messages?.map((message) => (
                    <Box
                      key={message.id}
                      sx={{
                        display: 'flex',
                        mb: 2,
                        justifyContent: message.direction === 'outbound' ? 'flex-end' : 'flex-start',
                      }}
                    >
                      <Box
                        sx={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          maxWidth: '70%',
                          flexDirection: message.direction === 'outbound' ? 'row-reverse' : 'row',
                        }}
                      >
                        <Avatar
                          sx={{
                            bgcolor: message.direction === 'outbound' ? 'primary.main' : 'grey.400',
                            mx: 1,
                          }}
                        >
                          {message.direction === 'outbound' ? <BotIcon /> : <PersonIcon />}
                        </Avatar>
                        <Card
                          sx={{
                            bgcolor: message.direction === 'outbound' ? 'primary.light' : 'grey.100',
                            color: message.direction === 'outbound' ? 'primary.contrastText' : 'text.primary',
                          }}
                        >
                          <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                            <Typography variant="body2">
                              {message.content}
                            </Typography>
                            <Typography
                              variant="caption"
                              sx={{
                                display: 'block',
                                mt: 1,
                                opacity: 0.7,
                              }}
                            >
                              {formatTimestamp(message.timestamp)}
                              {message.ai_generated && ' • AI Generated'}
                              {message.method === 'email' && ' • Email'}
                            </Typography>
                          </CardContent>
                        </Card>
                      </Box>
                    </Box>
                  ))}
                </Box>

                {/* Message Input */}
                <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
                  <Box display="flex" gap={1}>
                    <TextField
                      fullWidth
                      multiline
                      maxRows={3}
                      placeholder="Type your message..."
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage();
                        }
                      }}
                    />
                    <Button
                      variant="contained"
                      endIcon={<SendIcon />}
                      onClick={handleSendMessage}
                      disabled={!newMessage.trim() || sendMessageMutation.isLoading}
                    >
                      Send
                    </Button>
                  </Box>
                </Box>
              </>
            ) : (
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                }}
              >
                <Typography variant="h6" color="textSecondary">
                  Select a conversation to view messages
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Conversations;
