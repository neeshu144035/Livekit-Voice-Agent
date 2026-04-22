import os
import sys

# Read the original file
with open('main.py', 'r') as f:
    content = f.read()

# Chat agents code to add
chat_agents_code = '''


# Chat Agents - Added for Chat Feature
class ChatAgentModel(Base):
    __tablename__ = "chat_agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    system_prompt = Column(Text, default="")
    llm_model = Column(String(50), default="gpt-4o-mini")
    language = Column(String(10), default="en")
    custom_params = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatAgentCreate(BaseModel):
    name: str
    system_prompt: str = ""
    llm_model: str = "gpt-4o-mini"
    language: str = "en"
    custom_params: dict = {}


class ChatAgentUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    llm_model: Optional[str] = None
    language: Optional[str] = None
    custom_params: Optional[dict] = None


class ChatAgentResponse(BaseModel):
    id: int
    name: str
    system_prompt: str
    llm_model: str
    language: str
    custom_params: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessageRequest(BaseModel):
    message: str


# Create table
ChatAgentModel.__table__.create(bind=engine, checkfirst=True)


# Chat Agents Endpoints
@app.post("/api/chat-agents/", response_model=ChatAgentResponse, status_code=201)
async def create_chat_agent(agent_data: ChatAgentCreate, db: Session = Depends(get_database)):
    db_agent = ChatAgentModel(
        name=agent_data.name,
        system_prompt=agent_data.system_prompt,
        llm_model=agent_data.llm_model,
        language=agent_data.language,
        custom_params=agent_data.custom_params,
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent


@app.get("/api/chat-agents/", response_model=List[ChatAgentResponse])
async def list_chat_agents(db: Session = Depends(get_database)):
    return db.query(ChatAgentModel).order_by(ChatAgentModel.created_at.desc()).all()


@app.get("/api/chat-agents/{agent_id}", response_model=ChatAgentResponse)
async def get_chat_agent(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(ChatAgentModel).filter(ChatAgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Chat agent not found")
    return agent


@app.patch("/api/chat-agents/{agent_id}", response_model=ChatAgentResponse)
async def update_chat_agent(agent_id: int, agent_data: ChatAgentUpdate, db: Session = Depends(get_database)):
    agent = db.query(ChatAgentModel).filter(ChatAgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Chat agent not found")
    
    if agent_data.name is not None:
        agent.name = agent_data.name
    if agent_data.system_prompt is not None:
        agent.system_prompt = agent_data.system_prompt
    if agent_data.llm_model is not None:
        agent.llm_model = agent_data.llm_model
    if agent_data.language is not None:
        agent.language = agent_data.language
    if agent_data.custom_params is not None:
        agent.custom_params = agent_data.custom_params
    
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent


@app.delete("/api/chat-agents/{agent_id}")
async def delete_chat_agent(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(ChatAgentModel).filter(ChatAgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Chat agent not found")
    
    db.delete(agent)
    db.commit()
    return {"message": "Chat agent deleted successfully"}


@app.post("/api/chat-agents/{agent_id}/chat")
async def chat_with_agent(agent_id: int, chat_data: ChatMessageRequest, db: Session = Depends(get_database)):
    agent = db.query(ChatAgentModel).filter(ChatAgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Chat agent not found")
    
    messages = []
    if agent.system_prompt:
        messages.append({"role": "system", "content": agent.system_prompt})
    messages.append({"role": "user", "content": chat_data.message})
    
    try:
        from openai import OpenAI
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            return {"response": "OpenAI API key not configured. Please set OPENAI_API_KEY in environment."}
        
        client = OpenAI(api_key=openai_api_key)
        
        response = client.chat.completions.create(
            model=agent.llm_model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )
        
        return {"response": response.choices[0].message.content}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"response": f"Sorry, I encountered an error: {str(e)}"}
'''

# Check if already added
if 'class ChatAgentModel(Base):' in content:
    print("Chat agents already added!")
    sys.exit(0)

# Append the code
content += chat_agents_code

# Write back
with open('main.py', 'w') as f:
    f.write(content)

print("Chat agents added successfully!")
