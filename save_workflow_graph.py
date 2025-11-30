"""
Script to save the LangGraph workflow visualization.
"""
import sys
sys.path.insert(0, ".")

from src.app.agents.workflow import AnalysisWorkflow


def main():
    print("=" * 60)
    print("SAVING LANGGRAPH WORKFLOW VISUALIZATION")
    print("=" * 60)
    
    # Create workflow
    workflow = AnalysisWorkflow()
    
    print(f"\nAvailable modules: {workflow.available_modules}")
    print(f"Modules in graph: borrowings, equity_funding_mix\n")
    
    # Try to save as PNG
    try:
        output_path = workflow.save_graph_image("workflow_graph.png")
        print(f"✅ Graph PNG saved to: {output_path}")
    except ImportError as e:
        print(f"⚠️ Import error: {e}")
    except Exception as e:
        print(f"❌ PNG Error: {e}")
    
    # Also save Mermaid diagram
    try:
        graph = workflow.graph.get_graph()
        mermaid_code = graph.draw_mermaid()
        
        # Save mermaid code to file
        with open("workflow_graph.mmd", "w") as f:
            f.write(mermaid_code)
        print(f"✅ Mermaid diagram saved to: workflow_graph.mmd")
        
        # Also save as markdown with mermaid block for easy viewing
        with open("workflow_graph.md", "w") as f:
            f.write("# LangGraph Workflow Visualization\n\n")
            f.write("## Workflow Graph for Financial Analysis\n\n")
            f.write("This graph shows the flow between:\n")
            f.write("- **borrowings** - Debt/Borrowings Analysis Module\n")
            f.write("- **equity_funding_mix** - Equity Funding Mix Analysis Module\n\n")
            f.write("```mermaid\n")
            f.write(mermaid_code)
            f.write("\n```\n")
        print(f"✅ Markdown with Mermaid saved to: workflow_graph.md")
        
        print("\nMermaid Code:")
        print("-" * 40)
        print(mermaid_code)
        print("-" * 40)
        
    except Exception as e:
        print(f"⚠️ Mermaid error: {e}")
    
    # Also show ASCII representation
    print("\nASCII Graph Representation:")
    print("-" * 40)
    print(workflow.get_graph_visualization())
    print("-" * 40)
    
    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
