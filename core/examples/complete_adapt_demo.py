"""
Complete Self-Repair Demo
-------------------------
Demonstrates the FULL ADAPT pillar with automatic self-repair.

Shows:
1. Agent evaluation
2. Failure analysis
3. Improvement decision
4. Automatic code repair
5. Re-testing after fix

Run with:
    PYTHONPATH=core python core/examples/complete_adapt_demo.py
"""

from framework.adaptation import SelfRepairEngine


class MockAgent:
    """Mock agent for demonstration"""
    def __init__(self, accuracy=0.85, has_bug=False):
        self.accuracy = accuracy
        self.has_bug = has_bug
        self.call_count = 0
        
    def run(self, input_data):
        """Simulate agent execution"""
        import random
        self.call_count += 1
        
        # Simulate bug
        if self.has_bug and "email" not in input_data:
            raise ValueError("Missing required field 'email'")
        
        # Simulate success/failure based on accuracy
        success = random.random() < self.accuracy
        
        # Mock result
        class Result:
            def __init__(self, success):
                self.success = success
                self.output = {"result": "processed"} if success else None
                self.metrics = {"total_cost_usd": 0.001}
        
        return Result(success)


def main():
    print("🚀 COMPLETE SELF-REPAIR SYSTEM DEMO")
    print("="*60)
    print("\nDemonstrating Aden's ADAPT pillar:")
    print("  • Automatic performance monitoring")
    print("  • Intelligent failure analysis")
    print("  • Self-healing capabilities")
    print("  • Zero human intervention required")
    print("\n" + "="*60)
    
    # Create test cases
    test_cases = [
        {"input": {"email": f"user{i}@test.com", "name": f"User {i}"}, "expected": {"result": "processed"}}
        for i in range(20)
    ]
    
    # Add some cases that will trigger the bug
    for i in range(7):
        test_cases.append({"input": {"name": f"User {i}"}, "expected": None})  # Missing email!
    
    # Initialize self-repair engine
    repair_engine = SelfRepairEngine(
        agent_id="email-processor",
        agent_path="exports/email_processor"
    )
    
    # Create buggy agent
    print("\n" + "="*60)
    print("🐛 TESTING BUGGY AGENT (Has input validation bug)")
    print("="*60)
    
    buggy_agent = MockAgent(accuracy=0.70, has_bug=True)
    
    # Run complete diagnostic and repair cycle
    report = repair_engine.diagnose_and_repair(
        test_cases=test_cases,
        agent_runner=lambda x: buggy_agent.run(x),
        current_version="v1.0-buggy"
    )
    
    # Print results
    print("\n" + "="*60)
    print("📋 REPAIR REPORT")
    print("="*60)
    
    if report["repair_needed"]:
        print(f"\n🔴 Status: REPAIR NEEDED")
        print(f"📊 Metrics Before:")
        print(f"   Accuracy: {report['metrics_before']['accuracy']:.1%}")
        print(f"   Score: {report['metrics_before']['score']}/100")
        
        print(f"\n🎯 Decision:")
        print(f"   Priority: {report['decision']['priority'].upper()}")
        print(f"   Triggers: {', '.join(report['decision']['triggers'])}")
        
        print(f"\n🔧 Repairs Applied: {len(report['repairs_applied'])}")
        for repair in report['repairs_applied']:
            print(f"   • {repair['action']} in {repair['node_id']}")
        
        print(f"\n📈 Estimated Improvement:")
        print(f"   Accuracy: {report['estimated_improvement']['accuracy']}")
        print(f"   Success Rate: {report['estimated_improvement']['success_rate']}")
    else:
        print(f"\n✅ Status: HEALTHY")
        print(f"   Accuracy: {report['metrics'].accuracy:.1%}")
        print(f"   Score: {report['metrics'].get_score()}/100")
    
    # Show repair history
    repair_engine.print_repair_summary()
    
    # Demonstrate continuous monitoring
    print("\n" + "="*60)
    print("🔄 CONTINUOUS MONITORING MODE")
    print("="*60)
    print("\nSimulating production environment with auto-repair...")
    
    # Use smaller test set for continuous monitoring demo
    small_test_set = test_cases[:10]
    
    monitoring_report = repair_engine.continuous_monitoring_cycle(
        test_cases=small_test_set,
        agent_runner=lambda x: buggy_agent.run(x),
        max_repair_attempts=3
    )
    
    print(f"\n📊 Monitoring Summary:")
    print(f"   Total Cycles: {monitoring_report['total_cycles']}")
    print(f"   Repairs Applied: {monitoring_report['repairs_applied']}")
    print(f"   Final Status: {monitoring_report['final_status'].upper()}")
    
    print("\n" + "="*60)
    print("✅ DEMO COMPLETE")
    print("="*60)
    
    print("\n🎯 Key Capabilities Demonstrated:")
    print("   ✅ Automatic performance evaluation")
    print("   ✅ Intelligent failure pattern detection")
    print("   ✅ Priority-based improvement decisions")
    print("   ✅ Automated code repair generation")
    print("   ✅ Continuous self-monitoring")
    print("   ✅ Zero human intervention required")
    
    print("\n💡 Production Benefits:")
    print("   • Agents that fix themselves when they break")
    print("   • Continuous quality improvement")
    print("   • Reduced maintenance costs")
    print("   • Enterprise-grade reliability")
    print("   • Competitive advantage over static frameworks\n")


if __name__ == "__main__":
    main()
