"""FastAPI application for the RAG pipeline."""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import time

from app.config import Settings
from app.schemas import (
    RAGRequest,
    RAGResponse,
    HealthResponse,
    ErrorResponse,
    IntentClassification,
)
from app.gateway import LiteLLMGateway
from app.intent_classifier import IntentClassifier
from app.model_router import ModelRouter
from app.rag_pipeline import RAGPipeline, create_sample_documents


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.
    
    Args:
        settings: Optional Settings instance (creates default if None)
        
    Returns:
        Configured FastAPI application
    """
    if settings is None:
        settings = Settings()
    
    app = FastAPI(
        title="LiteLLM + Haystack RAG Pipeline",
        description="A minimal RAG pipeline with intent classification and model routing",
        version="1.0.0",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize components
    gateway = LiteLLMGateway(settings)
    intent_classifier = IntentClassifier(settings, gateway)
    model_router = ModelRouter(settings, gateway)
    rag_pipeline = RAGPipeline(
        settings=settings,
        litellm_base_url=settings.litellm_base_url,
        api_key=settings.litellm_api_key,
    )
    
    # Store components in app state for access in routes
    app.state.settings = settings
    app.state.gateway = gateway
    app.state.intent_classifier = intent_classifier
    app.state.model_router = model_router
    app.state.rag_pipeline = rag_pipeline
    
    # Register shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        await gateway.close()
    
    # Initialize with sample documents
    sample_docs = create_sample_documents()
    rag_pipeline.add_documents(sample_docs)
    
    # Register routes
    register_routes(app, settings)
    
    return app


def register_routes(app: FastAPI, settings: Settings):
    """Register API routes.
    
    Args:
        app: FastAPI application
        settings: Application settings
    """
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Check service health and LiteLLM gateway availability."""
        gateway = app.state.gateway
        
        litellm_healthy = await gateway.check_health()
        
        return HealthResponse(
            status="healthy" if litellm_healthy else "degraded",
            litellm_gateway=litellm_healthy,
            timestamp=datetime.utcnow().isoformat()
        )
    
    @app.post(
        "/rag/query",
        response_model=RAGResponse,
        responses={
            500: {"model": ErrorResponse, "description": "Internal server error"}
        }
    )
    async def rag_query(request: RAGRequest):
        """Process a RAG query through the full pipeline.
        
        This endpoint:
        1. Classifies the user's intent
        2. Routes to an appropriate model based on classification
        3. Retrieves relevant documents
        4. Generates a response using the selected model
        
        Args:
            request: RAGRequest with query and options
            
        Returns:
            RAGResponse with answer, model used, and optional sources
        """
        start_time = time.time()
        
        try:
            # Get components
            intent_classifier = app.state.intent_classifier
            model_router = app.state.model_router
            rag_pipeline = app.state.rag_pipeline
            gateway = app.state.gateway
            
            # Step 1: Classify intent
            intent = await intent_classifier.classify_with_timeout(request.query)
            
            # Step 2: Route to appropriate model
            routing_decision = model_router.route(intent)
            
            # Step 3: Execute RAG pipeline with selected model
            answer, sources = await rag_pipeline.query(
                query=request.query,
                model=routing_decision.selected_model,
                top_k=settings.max_retrieved_docs,
                include_sources=request.include_sources,
            )
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Build response
            response = RAGResponse(
                answer=answer,
                model_used=routing_decision.selected_model,
                intent=intent if settings.debug else None,
                sources=sources if request.include_sources else None,
                processing_time_ms=processing_time_ms,
            )
            
            return response
            
        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            
            if settings.debug:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to process RAG query"
                )
    
    @app.get("/models", response_model=dict[str, str])
    async def list_models():
        """List available models by tier.
        
        Returns:
            Dictionary mapping tier names to model identifiers
        """
        model_router = app.state.model_router
        return model_router.get_all_available_models()
    
    @app.get("/routing/explain/{intent_type}")
    async def explain_routing(intent_type: str):
        """Explain routing strategy for a given intent type.
        
        Args:
            intent_type: One of simple, complex, technical, creative
            
        Returns:
            Explanation of routing strategy
        """
        from app.schemas import IntentType
        
        try:
            intent = IntentType(intent_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid intent type: {intent_type}. Must be one of: simple, complex, technical, creative"
            )
        
        model_router = app.state.model_router
        return {
            "intent_type": intent.value,
            "explanation": model_router.explain_routing_for_intent(intent)
        }
    
    @app.post("/documents/initialize")
    async def initialize_documents():
        """Initialize document store with sample documents.
        
        Returns:
            Number of documents added
        """
        rag_pipeline = app.state.rag_pipeline
        rag_pipeline.clear_documents()
        
        sample_docs = create_sample_documents()
        count = rag_pipeline.add_documents(sample_docs)
        
        return {"documents_added": count}
    
    @app.get("/documents/count")
    async def get_document_count():
        """Get the number of documents in the store.
        
        Returns:
            Document count
        """
        rag_pipeline = app.state.rag_pipeline
        return {"count": rag_pipeline.get_document_count()}


# Create the app instance
settings = Settings()
app = create_app(settings)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
